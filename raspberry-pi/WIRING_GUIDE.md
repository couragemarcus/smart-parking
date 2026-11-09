# HC-SR04 Wiring Guide — Smart Parking System

## ⚠️ CRITICAL VOLTAGE WARNING

> **The HC-SR04 echo pin outputs 5 V. Raspberry Pi GPIO pins are rated for 3.3 V maximum.
> Connecting the echo pin directly WILL damage the Raspberry Pi.**
> You MUST use a voltage divider or level-shifter before connecting ECHO to GPIO.

---

## Components Required

| Component | Qty | Notes |
|-----------|-----|-------|
| HC-SR04 ultrasonic sensor | 1 | |
| Resistor 1 kΩ | 1 | Part of voltage divider |
| Resistor 2 kΩ | 1 | Part of voltage divider |
| Jumper wires (female-female) | 4+ | |
| Breadboard | 1 | Optional but recommended |

---

## Voltage Divider Circuit

```
HC-SR04 ECHO (5V)
        │
       [1kΩ]
        │
        ├─────────────────────────► Pi GPIO ECHO_PIN (pin 18, BCM 24)
        │                           reads ~3.3V — safe!
       [2kΩ]
        │
       GND ◄───────────────────────  Pi GND
```

The divider produces: `V_out = 5V × 2000 / (1000 + 2000) ≈ 3.33V` ✓

---

## Full Wiring Table

| HC-SR04 Pin | Wire Colour | Connection |
|-------------|-------------|------------|
| VCC | Red | Pi Pin 2 (5V) |
| GND | Black | Pi Pin 6 (GND) |
| TRIG | Yellow | Pi Pin 12 (BCM 18) — direct, 3.3V output is sufficient |
| ECHO | Orange | → 1kΩ resistor → Pi Pin 18 (BCM 24) |
| | | also connect junction to 2kΩ → GND |

---

## Raspberry Pi GPIO Pin Reference (BCM)

```
                    3V3  (1) (2)  5V
                  GPIO2  (3) (4)  5V
                  GPIO3  (5) (6)  GND ◄── HC-SR04 GND
                  GPIO4  (7) (8)  GPIO14
                    GND  (9)(10)  GPIO15
                 GPIO17 (11)(12)  GPIO18 ◄── HC-SR04 TRIG (BCM 18)
                 GPIO27 (13)(14)  GND
                 GPIO22 (15)(16)  GPIO23
                    3V3 (17)(18)  GPIO24 ◄── HC-SR04 ECHO via divider (BCM 24)
                 GPIO10 (19)(20)  GND
                  GPIO9 (21)(22)  GPIO25
                 GPIO11 (23)(24)  GPIO8
                    GND (25)(26)  GPIO7
```

Default configuration:
- **TRIG** → BCM 18 (Pin 12)
- **ECHO** → BCM 24 (Pin 18) via voltage divider

---

## Sensor Placement Guide

```
    PARKING LOT ENTRANCE
    ════════════════════

    [WALL/POST]   [WALL/POST]
         │                │
    ┌────┴──────────────┬─┘
    │ ← lane width ~3m → │
    │                    │
    └────────────────────┘
         ▲
    HC-SR04 mounted at ~80cm height
    pointing horizontally across lane
    (not downward — avoid ground reflections)
```

### Placement Tips
- Mount at bumper height (~50–80 cm from ground)
- Aim horizontally across the lane, not downward
- Keep sensor out of direct sunlight (IR interference)
- Avoid mounting near reflective surfaces at sharp angles
- Test threshold with the `HARDWARE_MODE=false` mock first
- Adjust `DETECTION_THRESHOLD_CM` to 60–80% of lane width

---

## Calibration Procedure

1. Set `HARDWARE_MODE=true` in `.env`
2. Set `DETECTION_THRESHOLD_CM=200` (large threshold)
3. Run sensor service, observe logged distances:
   ```
   sudo journalctl -u parking-sensor -f
   ```
4. Note the distance when no vehicle is present (e.g. 380 cm)
5. Drive a vehicle into the lane, note detected distance (e.g. 35 cm)
6. Set threshold to midpoint × 0.8 (e.g. 150 cm)
7. Adjust `HYSTERESIS_COUNT=3` (require 3 consecutive readings)

---

## Optional: Individual Space Sensors

Each parking space can have its own HC-SR04 (or IR/photoelectric sensor):
- Mount above space, pointing downward
- Use separate GPIO pins per sensor
- Wire same voltage divider for each ECHO pin
- These sensors trigger `POST /api/iot/space-status` (not `/api/iot/arrival`)
- Without individual sensors: require manual security confirmation or "I Have Arrived" button

---

## Software Configuration (`.env`)

```dotenv
HARDWARE_MODE=true
GPIO_TRIGGER_PIN=18    # BCM numbering
GPIO_ECHO_PIN=24       # BCM numbering
DETECTION_THRESHOLD_CM=50.0
POLL_INTERVAL_S=0.1
COOLDOWN_S=5.0
HYSTERESIS_COUNT=3
BACKEND_URL=https://your-server.example.com
DEVICE_ID=rpi-sensor-01
DEVICE_SECRET=your-secret-here
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Pi GPIO damaged | Direct 5V echo connection | Use voltage divider — see above |
| No readings / always 999 cm | Echo timeout | Check wiring; ensure ECHO sees ~3.3V |
| Erratic readings | No hysteresis | Increase `HYSTERESIS_COUNT` |
| Multiple arrivals per vehicle | No cooldown | Increase `COOLDOWN_S` |
| Service won't start | GPIO permissions | Run `sudo usermod -aG gpio pi` |
| Can't connect to backend | Network/URL | Check `BACKEND_URL` and firewall |
