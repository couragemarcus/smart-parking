"""
Raspberry Pi Sensor Service for Smart Parking System.

Runs as a standalone process on the Raspberry Pi. Reads the entry
sensor in a loop and POST s authenticated arrival events to the
FastAPI backend.

Configuration (environment variables / .env file):
    BACKEND_URL         URL of the FastAPI backend (e.g. https://parking.example.com)
    DEVICE_ID           Credential: device identifier
    DEVICE_SECRET       Credential: shared secret
    GPIO_TRIGGER_PIN    HC-SR04 trigger GPIO (BCM), default 18
    GPIO_ECHO_PIN       HC-SR04 echo GPIO (BCM), default 24
    DETECTION_THRESHOLD_CM  Vehicle presence threshold, default 50.0
    HARDWARE_MODE       "true" for real HC-SR04, "false" for mock
    POLL_INTERVAL_S     Polling interval in seconds, default 0.1
    COOLDOWN_S          Seconds to ignore sensor after detection, default 5.0
    HYSTERESIS_COUNT    Consecutive readings below threshold to confirm, default 3

See gpio_adapter.py for voltage-divider wiring instructions.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sensor_service")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
DEVICE_ID: str = os.getenv("DEVICE_ID", "rpi-sensor-01")
DEVICE_SECRET: str = os.getenv("DEVICE_SECRET", "change-device-secret")
TRIGGER_PIN: int = int(os.getenv("GPIO_TRIGGER_PIN", "18"))
ECHO_PIN: int = int(os.getenv("GPIO_ECHO_PIN", "24"))
DETECTION_THRESHOLD_CM: float = float(os.getenv("DETECTION_THRESHOLD_CM", "50.0"))
HARDWARE_MODE: bool = os.getenv("HARDWARE_MODE", "false").lower() == "true"
POLL_INTERVAL_S: float = float(os.getenv("POLL_INTERVAL_S", "0.1"))
COOLDOWN_S: float = float(os.getenv("COOLDOWN_S", "5.0"))
HYSTERESIS_COUNT: int = int(os.getenv("HYSTERESIS_COUNT", "3"))

# ---------------------------------------------------------------------------
# Import adapter
# ---------------------------------------------------------------------------
from gpio_adapter import get_adapter, HardwareAdapter  # noqa: E402


class SensorService:
    """
    Main sensor polling loop with hysteresis and cooldown.

    Algorithm:
        1. Poll distance every POLL_INTERVAL_S seconds.
        2. Count consecutive readings ≤ threshold → hysteresis buffer.
        3. When HYSTERESIS_COUNT readings confirm detection, fire arrival event.
        4. Enter cooldown for COOLDOWN_S seconds (ignore further readings).
        5. After cooldown, start monitoring for departure (readings > threshold).
        6. Repeat.
    """

    def __init__(self, adapter: HardwareAdapter) -> None:
        self.adapter = adapter
        self._client = httpx.AsyncClient(timeout=10.0)
        self._running = False

    async def start(self) -> None:
        """Initialise hardware and start the sensor loop."""
        await self.adapter.initialize()
        self._running = True
        logger.info(
            "Sensor service started. Backend: %s | Mode: %s | Threshold: %.1f cm",
            BACKEND_URL,
            "HARDWARE" if HARDWARE_MODE else "MOCK",
            DETECTION_THRESHOLD_CM,
        )
        try:
            await self._run_loop()
        finally:
            await self._client.aclose()
            await self.adapter.cleanup()

    async def stop(self) -> None:
        self._running = False

    async def _run_loop(self) -> None:
        """Main polling loop with hysteresis and cooldown."""
        consecutive_detections = 0
        in_cooldown = False
        cooldown_until = 0.0

        while self._running:
            now = time.monotonic()

            if in_cooldown:
                if now < cooldown_until:
                    await asyncio.sleep(POLL_INTERVAL_S)
                    continue
                else:
                    in_cooldown = False
                    consecutive_detections = 0
                    logger.info("Cooldown ended. Resuming monitoring.")

            try:
                distance = await self.adapter.read_distance_cm()
            except Exception as exc:
                logger.error("Sensor read error: %s", exc)
                await asyncio.sleep(1.0)
                continue

            detected = self.adapter.is_vehicle_detected(distance, DETECTION_THRESHOLD_CM)

            if detected:
                consecutive_detections += 1
                logger.debug(
                    "Detection %d/%d at %.1f cm",
                    consecutive_detections,
                    HYSTERESIS_COUNT,
                    distance,
                )
                if consecutive_detections >= HYSTERESIS_COUNT:
                    logger.info(
                        "VEHICLE DETECTED at %.1f cm (confirmed after %d readings)",
                        distance,
                        HYSTERESIS_COUNT,
                    )
                    await self._send_arrival_event(distance)
                    in_cooldown = True
                    cooldown_until = time.monotonic() + COOLDOWN_S
                    consecutive_detections = 0
            else:
                consecutive_detections = 0

            await asyncio.sleep(POLL_INTERVAL_S)

    async def _send_arrival_event(self, distance_cm: float) -> None:
        """POST an arrival event to the FastAPI backend."""
        idempotency_key = f"{DEVICE_ID}-{uuid.uuid4()}"
        payload: dict[str, Any] = {
            "idempotency_key": idempotency_key,
            "sensor_type": "ultrasonic_hcsr04" if HARDWARE_MODE else "mock",
            "raw_distance_cm": distance_cm,
        }
        headers = {
            "X-Device-Id": DEVICE_ID,
            "X-Device-Secret": DEVICE_SECRET,
            "Content-Type": "application/json",
        }

        for attempt in range(3):
            try:
                response = await self._client.post(
                    f"{BACKEND_URL}/api/iot/arrival",
                    json=payload,
                    headers=headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    logger.info(
                        "Arrival event sent. access=%s, session_matched=%s, space=%s",
                        data.get("access", "BLOCKED"),
                        data.get("session_matched", False),
                        data.get("space_name"),
                    )
                    return
                elif response.status_code == 409:
                    logger.info("Duplicate arrival event (idempotency key already processed).")
                    return
                else:
                    logger.warning(
                        "Arrival event rejected: HTTP %d – %s",
                        response.status_code,
                        response.text[:200],
                    )
            except httpx.RequestError as exc:
                logger.error(
                    "Network error sending arrival (attempt %d/3): %s",
                    attempt + 1,
                    exc,
                )
                await asyncio.sleep(2 ** attempt)

        logger.error("Failed to send arrival event after 3 attempts.")


async def main() -> None:
    """Entry point."""
    adapter = get_adapter(
        hardware_mode=HARDWARE_MODE,
        trigger_pin=TRIGGER_PIN,
        echo_pin=ECHO_PIN,
    )
    service = SensorService(adapter)

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Shutting down sensor service...")
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
