#!/bin/bash
# Setup script for Raspberry Pi LED Display Client
# Run once after cloning the project on the Pi:
#   chmod +x setup.sh && sudo ./setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== LDW LED Display - Pi Setup ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run with sudo: sudo ./setup.sh"
    exit 1
fi

# Get the actual user (not root)
REAL_USER="${SUDO_USER:-pi}"
REAL_HOME=$(eval echo "~$REAL_USER")

echo "[1/5] Updating system packages..."
apt update && apt upgrade -y

echo "[2/5] Installing build dependencies..."
apt install -y python3 python3-pip git python3-dev cython3 cmake python3-pil

echo "[3/5] Building and installing rpi-rgb-led-matrix Python bindings..."
if [ ! -d "$REAL_HOME/rpi-rgb-led-matrix" ]; then
    sudo -u "$REAL_USER" git clone https://github.com/hzeller/rpi-rgb-led-matrix.git "$REAL_HOME/rpi-rgb-led-matrix"
fi
cd "$REAL_HOME/rpi-rgb-led-matrix"
pip3 install pillow --break-system-packages
pip3 install . --break-system-packages

echo "[4/5] Installing Python dependencies..."
cd "$SCRIPT_DIR"
pip3 install -r requirements.txt --break-system-packages

echo "[5/5] Copying fonts to pi-client directory..."
FONTS_SRC="$REAL_HOME/rpi-rgb-led-matrix/fonts"
FONTS_DST="$SCRIPT_DIR/fonts"
if [ -d "$FONTS_SRC" ]; then
    mkdir -p "$FONTS_DST"
    cp "$FONTS_SRC"/*.bdf "$FONTS_DST/" 2>/dev/null || true
    chown -R "$REAL_USER:$REAL_USER" "$FONTS_DST"
    echo "  Copied BDF fonts to $FONTS_DST"
else
    echo "  WARNING: Font source not found at $FONTS_SRC"
fi

echo "[6/6] Disabling on-board audio (conflicts with LED GPIO)..."
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="/boot/config.txt"
fi
if ! grep -q "dtparam=audio=off" "$CONFIG_FILE"; then
    echo "dtparam=audio=off" >> "$CONFIG_FILE"
    echo "  Audio disabled in $CONFIG_FILE"
else
    echo "  Audio already disabled"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit config.py and set SERVER_URL to your server's IP"
echo "  2. Reboot: sudo reboot"
echo "  3. Test: sudo python3 client.py --led-rows=64 --led-cols=64 --led-chain=4 --led-parallel=2 --led-slowdown-gpio=4"
echo ""
