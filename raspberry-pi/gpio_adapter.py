"""
GPIO Adapter for Smart Parking Sensor Service.

Provides an abstraction layer between the sensor logic and the
underlying hardware so that the same parking allocation logic runs
in both simulation and real hardware modes.

Hardware WARNING:
    The HC-SR04 echo pin outputs 5 V. Raspberry Pi GPIO is rated for
    3.3 V maximum. Direct connection WILL damage the Pi. Use a voltage
    divider (e.g. 1kΩ + 2kΩ) or a dedicated level-shifter module
    between the HC-SR04 echo pin and the GPIO input pin.

    Wiring (with resistor divider):
        HC-SR04 VCC  -> Pi 5V  (pin 2)
        HC-SR04 GND  -> Pi GND (pin 6)
        HC-SR04 TRIG -> Pi GPIO TRIGGER_PIN (3.3V output, direct)
        HC-SR04 ECHO -> 1kΩ resistor -> Pi GPIO ECHO_PIN
                        junction of 1kΩ and 2kΩ -> Pi GPIO ECHO_PIN
                        2kΩ resistor -> Pi GND

    This divides 5V echo to ~3.3V: safe for GPIO input.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class HardwareAdapter(ABC):
    """Abstract interface for distance-sensing hardware."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialise GPIO/hardware resources."""

    @abstractmethod
    async def read_distance_cm(self) -> float:
        """Return measured distance in centimetres."""

    @abstractmethod
    async def cleanup(self) -> None:
        """Release GPIO/hardware resources."""

    def is_vehicle_detected(self, distance_cm: float, threshold_cm: float) -> bool:
        """Return True when a vehicle is within threshold_cm."""
        return distance_cm <= threshold_cm


class HCSR04Adapter(HardwareAdapter):
    """
    HC-SR04 ultrasonic sensor via Raspberry Pi GPIO.

    Environment variables (via sensor_service.py / .env):
        GPIO_TRIGGER_PIN  (default 18)
        GPIO_ECHO_PIN     (default 24)

    See module docstring for voltage-divider wiring.
    """

    SPEED_OF_SOUND_CM_S = 34300  # cm/s at ~20 °C

    def __init__(self, trigger_pin: int = 18, echo_pin: int = 24) -> None:
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self._gpio: object | None = None

    async def initialize(self) -> None:
        """Set up GPIO pins."""
        try:
            import RPi.GPIO as GPIO  # type: ignore[import]
            self._gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.trigger_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            GPIO.output(self.trigger_pin, False)
            # Let sensor settle
            await asyncio.sleep(0.5)
            logger.info(
                "HC-SR04 initialised: TRIG=%d, ECHO=%d",
                self.trigger_pin,
                self.echo_pin,
            )
        except ImportError:
            logger.error(
                "RPi.GPIO not available. Are you running on Raspberry Pi?"
            )
            raise

    async def read_distance_cm(self) -> float:
        """
        Trigger HC-SR04 pulse and measure echo duration.

        Returns distance in centimetres or 999.0 on timeout.
        """
        GPIO = self._gpio
        if GPIO is None:
            raise RuntimeError("Adapter not initialised. Call initialize() first.")

        # Send 10 µs trigger pulse
        GPIO.output(self.trigger_pin, True)
        await asyncio.sleep(0.00001)  # 10 µs
        GPIO.output(self.trigger_pin, False)

        timeout = time.monotonic() + 0.04  # 40 ms max

        # Wait for echo to go high
        pulse_start = time.monotonic()
        while GPIO.input(self.echo_pin) == 0:
            pulse_start = time.monotonic()
            if pulse_start > timeout:
                logger.warning("HC-SR04 echo timeout (waiting for HIGH)")
                return 999.0

        # Wait for echo to go low
        pulse_end = time.monotonic()
        while GPIO.input(self.echo_pin) == 1:
            pulse_end = time.monotonic()
            if pulse_end > timeout:
                logger.warning("HC-SR04 echo timeout (waiting for LOW)")
                return 999.0

        duration = pulse_end - pulse_start
        distance = (duration * self.SPEED_OF_SOUND_CM_S) / 2
        return round(distance, 1)

    async def cleanup(self) -> None:
        """Release GPIO resources."""
        if self._gpio is not None:
            self._gpio.cleanup()
            logger.info("GPIO cleaned up.")


class MockAdapter(HardwareAdapter):
    """
    Mock adapter for testing and simulation on non-Pi hardware.

    Cycle through a configurable sequence of distances to simulate
    vehicle approaching and leaving.
    """

    def __init__(self, distances: list[float] | None = None) -> None:
        # Default: far -> approaching -> detected -> departing -> far
        self._distances = distances or [
            200.0, 180.0, 120.0, 80.0, 40.0, 40.0, 80.0, 200.0
        ]
        self._index = 0
        self._override: float | None = None

    async def initialize(self) -> None:
        logger.info("MockAdapter initialised (simulation mode).")

    async def read_distance_cm(self) -> float:
        if self._override is not None:
            return self._override
        distance = self._distances[self._index % len(self._distances)]
        self._index += 1
        return distance

    async def cleanup(self) -> None:
        logger.info("MockAdapter cleaned up.")

    def set_distance(self, distance_cm: float) -> None:
        """Force a specific distance for the next reading(s)."""
        self._override = distance_cm

    def clear_override(self) -> None:
        self._override = None


def get_adapter(hardware_mode: bool, trigger_pin: int, echo_pin: int) -> HardwareAdapter:
    """Factory: return the appropriate adapter based on mode."""
    if hardware_mode:
        return HCSR04Adapter(trigger_pin=trigger_pin, echo_pin=echo_pin)
    return MockAdapter()
