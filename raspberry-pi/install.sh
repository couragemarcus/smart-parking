#!/usr/bin/env bash
# Smart Parking System — Raspberry Pi Installation Script
# Tested on Raspberry Pi OS (Bookworm / Bullseye), Python 3.11+

set -euo pipefail

INSTALL_DIR="/opt/smart-parking-sensor"
SERVICE_FILE="/etc/systemd/system/parking-sensor.service"
PYTHON="python3"
PIP="pip3"

echo "=========================================="
echo " Smart Parking Sensor Service Installer"
echo "=========================================="

# ---- 1. System dependencies -----------------------------------------------
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git

# ---- 2. Copy files --------------------------------------------------------
echo "[2/6] Copying service files to $INSTALL_DIR..."
sudo mkdir -p "$INSTALL_DIR"
sudo cp sensor_service.py gpio_adapter.py requirements.txt "$INSTALL_DIR/"

# ---- 3. Python venv + deps ------------------------------------------------
echo "[3/6] Creating virtual environment..."
sudo python3 -m venv "$INSTALL_DIR/venv"
sudo "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
sudo "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# ---- 4. .env file ---------------------------------------------------------
echo "[4/6] Creating .env configuration..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    sudo tee "$INSTALL_DIR/.env" > /dev/null <<'EOF'
# Backend API endpoint (update to your server's address)
BACKEND_URL=http://192.168.1.100:8000

# Device authentication (must match backend DEVICE_ID / DEVICE_SECRET)
DEVICE_ID=rpi-sensor-01
DEVICE_SECRET=change-device-secret

# HC-SR04 GPIO pins (BCM numbering)
GPIO_TRIGGER_PIN=18
GPIO_ECHO_PIN=24

# Vehicle detection threshold in centimetres
DETECTION_THRESHOLD_CM=50.0

# Set to "true" for real HC-SR04, "false" for mock/simulation
HARDWARE_MODE=true

# Polling interval (seconds between readings)
POLL_INTERVAL_S=0.1

# Cooldown after detection (seconds)
COOLDOWN_S=5.0

# Consecutive readings required to confirm vehicle
HYSTERESIS_COUNT=3
EOF
    echo "  → Created $INSTALL_DIR/.env  (EDIT THIS FILE before starting the service)"
else
    echo "  → .env already exists, skipping."
fi

# ---- 5. systemd service ---------------------------------------------------
echo "[5/6] Installing systemd service..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Smart Parking Entry Sensor Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/python sensor_service.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable parking-sensor.service

# ---- 6. GPIO permissions --------------------------------------------------
echo "[6/6] Configuring GPIO access for user 'pi'..."
sudo usermod -aG gpio pi 2>/dev/null || true

echo ""
echo "=========================================="
echo " Installation complete!"
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo "  1. Edit $INSTALL_DIR/.env with your backend URL and credentials."
echo "  2. Wire the HC-SR04 sensor (see WIRING_GUIDE.md — use voltage divider on ECHO pin!)."
echo "  3. Start the service:  sudo systemctl start parking-sensor"
echo "  4. View logs:          sudo journalctl -u parking-sensor -f"
echo ""
