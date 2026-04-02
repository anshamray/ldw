# LDW LED Wall – Deployment Guide

This project has two parts:
1. **Server** (Node.js) – serves the web form and manages the message queue
2. **Pi Client** (Python) – runs on a Raspberry Pi connected to LED panels, polls the server for messages

**Repository:** `git@github.com:anshamray/ldw.git`

## Architecture Overview

```
┌──────────────┐        ┌──────────────┐        ┌──────────────────────┐
│  Visitors    │  HTTP   │   Server     │  HTTP   │  Raspberry Pi        │
│  (Phones)    │───────▶ │  (VPS/Local) │◀─────── │  + LED Panels        │
│  Web Form    │        │  Port 3000   │  Poll   │  pi-client/client.py │
└──────────────┘        └──────────────┘        └──────────────────────┘
```

Visitors submit messages via the web form → Server queues them (with a 1-minute moderation delay) → Pi Client polls for messages and displays them on the LED matrix.

---

## Part 1: Server Deployment

### Option A: Local Server (Recommended for LAN events)

Run the server on any machine in the same network as the Raspberry Pi.

```bash
# 1. Clone the repository
git clone git@github.com:anshamray/ldw.git
cd ldw

# 2. Install dependencies
npm install

# 3. (Optional) Set environment variables
export ADMIN_PASSWORD="YourSecurePassword"
export PORT=3000

# 4. Start the server
npm start
```

The server is now available at `http://<your-ip>:3000`.

> **Tip:** Find your machine's IP with `hostname -I` (Linux) or `ipconfig getifaddr en0` (macOS).

### Option B: VPS Deployment

For a public-facing server (e.g., visitors connect via QR code to a public URL).

#### Prerequisites
- A VPS (e.g., Hetzner, DigitalOcean, Netcup) with Ubuntu/Debian
- A domain name (optional but recommended)
- Node.js 18+ installed

#### Setup

```bash
# 1. SSH into your VPS
ssh user@your-vps-ip

# 2. Install Node.js (if not installed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 3. Clone and install
git clone git@github.com:anshamray/ldw.git
cd ldw
npm install

# 4. Create a systemd service for auto-start
sudo tee /etc/systemd/system/ldw-server.service > /dev/null << 'EOF'
[Unit]
Description=LDW LED Wall Message Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/user/ldw
ExecStart=/usr/bin/node server/index.js
Restart=always
RestartSec=5
Environment=PORT=3000
Environment=ADMIN_PASSWORD=YourSecurePassword
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

# 5. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ldw-server
sudo systemctl start ldw-server

# 6. Check status
sudo systemctl status ldw-server
```

#### Reverse Proxy with Nginx (for HTTPS)

```bash
sudo apt install nginx certbot python3-certbot-nginx

# Create Nginx config
sudo tee /etc/nginx/sites-available/ldw > /dev/null << 'EOF'
server {
    listen 80;
    server_name ldw.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/ldw /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Get SSL certificate (optional)
sudo certbot --nginx -d ldw.example.com
```

### Server Configuration

Edit `server/config.js` or set environment variables:

| Setting | Default | Env Var | Description |
|---------|---------|---------|-------------|
| `PORT` | `3000` | `PORT` | Server port |
| `ADMIN_PASSWORD` | `AusbildungIstCool` | `ADMIN_PASSWORD` | Admin panel password |
| `MAX_MESSAGE_LENGTH` | `200` | – | Max characters per message |
| `MESSAGE_DELAY_MS` | `60000` (1 min) | – | Delay before messages are shown (moderation window) |
| `RATE_LIMIT_MAX` | `3` | `RATE_LIMIT_MAX` | Max messages per IP per window |
| `RATE_LIMIT_WINDOW_MS` | `60000` | `RATE_LIMIT_WINDOW_MS` | Rate limit window in ms |

### Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Visitor web form |
| `/admin.html` | GET | Admin moderation panel |
| `/api/v1/messages` | POST | Submit a message |
| `/api/v1/messages/next` | GET | Get next message (used by Pi) |
| `/api/v1/messages/:id/displayed` | POST | Mark message as displayed |
| `/api/v1/health` | GET | Health check |
| `/api/v1/admin/messages` | GET | List all messages (auth required) |
| `/api/v1/admin/messages/:id` | DELETE | Delete a message (auth required) |

---

## Part 2: Raspberry Pi Setup

### Hardware

| Component | Details |
|-----------|---------|
| Raspberry Pi | **Pi 4 Model B** (tested and working) |
| LED Panels | Seengreat RGB-Matrix-P3.0-64×64, 1/32 scan, HUB75, 5 address lines (A–E) |
| HAT/Bonnet | Adafruit RGB Matrix Triple Bonnet (has 3 HUB75 outputs) |
| Power Supply | 5V, 40A+ (8 panels × ~4A each at full brightness) |
| Cables | HUB75 16-pin IDC ribbon cables (included with panels) |
| SD Card | 16GB+ with Raspberry Pi OS Lite (use genuine cards — counterfeits fail!) |

### Current Working Setup (April 2026)

**2 panels, direct GPIO wiring (bonnet bypassed — see Known Issues below).**

```
         Raspberry Pi 4
         ┌─────────────┐
         │  GPIO pins  │
         │  (direct)   │
         └──────┬──────┘
                │ jumper wires to HUB75
    ┌───────────┴───────────┐
    │ Panel 1  →  Panel 2   │   ← chain=2, parallel=1
    │  64x64      64x64     │
    └───────────────────────┘
    Total: 128 × 64 pixels
```

**Working command:**
```bash
sudo python3 pi-client/client.py --led-chain=2
```

Default flags (set in client.py): `--led-rows=64 --led-cols=64 --led-parallel=1 --led-hardware-mapping=regular --led-slowdown-gpio=4`

### Target Setup (with working bonnet)

**8 panels in 2×4 layout using Triple Bonnet's 3 HUB75 outputs.**

```
                   Raspberry Pi + Triple Bonnet
                   ┌─────────────────┐
                   │  HUB75 OUT #1   │── Chain 1 (4 panels)
                   │  HUB75 OUT #2   │── Chain 2 (4 panels)
                   │  HUB75 OUT #3   │   (unused)
                   └─────────────────┘

    ┌─────────┬─────────┬─────────┬─────────┐
    │ Panel 1 │ Panel 2 │ Panel 3 │ Panel 4 │  ← Top row (chain 1)
    │  64x64  │  64x64  │  64x64  │  64x64  │
    └─────────┴─────────┴─────────┴─────────┘

    ┌─────────┬─────────┬─────────┬─────────┐
    │ Panel 5 │ Panel 6 │ Panel 7 │ Panel 8 │  ← Bottom row (chain 2)
    │  64x64  │  64x64  │  64x64  │  64x64  │
    └─────────┴─────────┴─────────┴─────────┘

    Total resolution: 256 × 128 pixels
```

**Target command (once bonnet works):**
```bash
sudo python3 pi-client/client.py --led-chain=4 --led-parallel=2
```

### Direct GPIO Wiring (Bonnet Bypass)

Since the bonnet E-line is broken, we wire the Pi GPIO directly to the HUB75 input connector on the first panel. This uses the `regular` GPIO mapping from rpi-rgb-led-matrix.

```
Pi Physical Pin  →  HUB75 Pin (function)
─────────────────────────────────────────
(23) GPIO11      →  (1)  R1
(13) GPIO27      →  (2)  G1
(26) GPIO7       →  (3)  B1
(6)  GND         →  (4)  GND
(24) GPIO8       →  (5)  R2
(21) GPIO9       →  (6)  G2
(19) GPIO10      →  (7)  B2
(10) GPIO15      →  (8)  E      ← 5th address line (critical for 64×64)
(15) GPIO22      →  (9)  A
(16) GPIO23      →  (10) B
(18) GPIO24      →  (11) C
(22) GPIO25      →  (12) D
(11) GPIO17      →  (13) CLK
(7)  GPIO4       →  (14) LAT
(12) GPIO18      →  (15) OE
(14) GND         →  (16) GND
```

**HUB75 connector orientation:** The connector has 2 rows of 8 pins. Pin 1 is typically marked with an arrow or dot on the PCB. With the panel face-down and the connector at the top, pin numbering is:

```
 (1)  (2)  (3)  (4)  (5)  (6)  (7)  (8)
 (9)  (10) (11) (12) (13) (14) (15) (16)
```

**Limitation:** Direct wiring only supports 1 parallel chain (1 HUB75 output). To use multiple parallel chains, the bonnet is needed.

### Software Setup on Raspberry Pi

#### 1. Install Raspberry Pi OS Lite

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash **Raspberry Pi OS Lite (64-bit)** to an SD card.

During setup in the Imager:
- Set hostname: `ldw`
- Set username: `pi`
- Enable SSH (with password or key)
- Configure WiFi (or use Ethernet)

#### 2. One-Command Setup (Recommended)

```bash
ssh pi@ldw.local
git clone git@github.com:anshamray/ldw.git
cd ldw/pi-client
chmod +x setup.sh
sudo ./setup.sh
sudo reboot
```

The `setup.sh` script installs everything: build tools, rpi-rgb-led-matrix, Python dependencies, fonts, and disables audio.

#### 3. Manual Setup (if setup.sh fails)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install build tools
sudo apt install -y python3 python3-pip git cmake python3-dev cython3 python3-pil

# Clone and build rpi-rgb-led-matrix
cd ~
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix

# Build Python bindings (new method since March 2026 — PR #1865)
sudo pip3 install pillow --break-system-packages
sudo pip3 install . --break-system-packages

# Clone our project
cd ~
git clone git@github.com:anshamray/ldw.git
cd ldw/pi-client
pip3 install -r requirements.txt --break-system-packages

# Copy fonts (IMPORTANT — see Known Issues)
mkdir -p fonts
cp ~/rpi-rgb-led-matrix/fonts/*.bdf fonts/
```

#### 4. Critical System Configuration

All of these are **required** for the LED matrix to work correctly on Pi 4:

```bash
# a) Disable on-board audio (conflicts with GPIO 18 / OE pin)
# Add to /boot/firmware/config.txt:
dtparam=audio=off

# Also blacklist the kernel module:
echo "blacklist snd_bcm2835" | sudo tee /etc/modprobe.d/blacklist-sound.conf

# b) Disable serial console (conflicts with GPIO 15 / E-line)
sudo raspi-config
# → Interface Options → Serial Port → "No" to login shell → "No" to serial hardware

# c) Disable 1-wire interface (can conflict with GPIO)
# In /boot/firmware/config.txt, comment out or remove:
# dtoverlay=w1-gpio

# d) Improve real-time performance (optional but recommended)
# Add to /boot/firmware/cmdline.txt (at the end of the existing line):
isolcpus=3

# e) Reboot after all changes
sudo reboot
```

#### 5. Configure the Client

Edit `pi-client/config.py`:

```python
SERVER_URL = "http://172.16.155.51:3000"   # your server's IP
DISPLAY_ID = "pi-01"
DISPLAY_TIME = 10
POLL_INTERVAL = 2
```

#### 6. Test the Display

```bash
cd ~/ldw

# Test with C++ demos first (from rpi-rgb-led-matrix)
cd ~/rpi-rgb-led-matrix
sudo ./demo -D 0 --led-rows=64 --led-cols=64 --led-chain=2 --led-slowdown-gpio=4

# Then test the Python client
cd ~/ldw
sudo python3 pi-client/client.py --led-chain=2
```

#### 7. Auto-Start on Boot

```bash
sudo tee /etc/systemd/system/ldw-display.service > /dev/null << 'EOF'
[Unit]
Description=LDW LED Display Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/ldw/pi-client
ExecStart=/usr/bin/python3 client.py --led-chain=2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ldw-display
sudo systemctl start ldw-display
```

**Check logs:**
```bash
sudo journalctl -u ldw-display -f
```

---

## Known Issues & Lessons Learned

### 1. Adafruit Triple Bonnet E-line broken (UNRESOLVED)

**Symptom:** With the bonnet, 64×64 panels show "2 rows lit, 2 rows dark" stripe pattern.

**Root cause:** The bonnet's E-line (5th address line, GPIO 15 → HUB75 pin 8) is not passing the signal to the panels. 64×64 panels need address lines A–E; without E, only 32 rows can be addressed, causing the stripe pattern.

**What was tried (none worked):**
- All 108 combinations of `--led-multiplexing` (0–17) × `--led-row-addr-type` (0–5)
- Both E-line switch positions (4 and 8)
- `--led-gpio-mapping=regular` and `--led-gpio-mapping=adafruit-hat`
- Disabling audio, serial console, 1-wire

**What works:** Direct GPIO wiring (bypassing the bonnet) with the exact same pins → panels display perfectly. This proves the panels and Pi are fine.

**Possible causes:** Defective bonnet, bad E-line switch, level shifter issue, or missing solder bridge.

**Workaround:** Use direct GPIO wiring (limits to 1 parallel chain / single HUB75 output).

### 2. Font loading must happen before RGBMatrix init

The `RGBMatrix()` constructor **drops root privileges** after initializing GPIO. Any file access after that point fails silently (`os.path.exists()` returns `False` for readable files). The client code loads fonts **before** creating the matrix to avoid this.

If fonts aren't found, copy them into the project:
```bash
mkdir -p ~/ldw/pi-client/fonts
cp ~/rpi-rgb-led-matrix/fonts/*.bdf ~/ldw/pi-client/fonts/
```

### 3. rpi-rgb-led-matrix build process changed (March 2026)

As of PR #1865, the old `make build-python` no longer works. The new method uses `pip3 install .` with scikit-build-core + cmake. Requires `cmake python3-dev cython3`.

### 4. Counterfeit SD cards

We lost time debugging boot failures that turned out to be a counterfeit SD card. Buy from trusted sources (e.g., official Raspberry Pi resellers).

### 5. Pi 4 GPIO timing

Pi 4 needs `--led-slowdown-gpio=4` to avoid flickering. Pi 3 typically needs `--led-slowdown-gpio=2`.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "2 rows lit, 2 rows dark" | E-line issue — see Known Issue #1. Try direct wiring. |
| Flickering / ghosting | Increase `--led-slowdown-gpio` (try 2, 3, or 4) |
| "Could not find BDF font file" | Copy fonts: `cp ~/rpi-rgb-led-matrix/fonts/*.bdf ~/ldw/pi-client/fonts/` |
| Connection error to server | Check `pi-client/config.py` — make sure `SERVER_URL` is correct |
| `git pull` fails with "untracked files" | Run `git clean -fd && git checkout -- . && git pull` |
| Panel shows nothing | Check 5V power to panels. Run `sudo ./demo -D 0 ...` to test hardware. |
| `rgbmatrix` module not found | Re-install: `cd ~/rpi-rgb-led-matrix && sudo pip3 install . --break-system-packages` |
| Audio interference / artifacts | Verify `dtparam=audio=off` in config.txt AND `blacklist snd_bcm2835` |

---

## Event Day Checklist

- [ ] Server is running and accessible (test: `curl http://<server-ip>:3000/api/v1/health`)
- [ ] Pi is connected to the network and can reach the server
- [ ] LED panels are powered and displaying text
- [ ] Admin panel is accessible at `http://<server-ip>:3000/admin.html`
- [ ] QR code printed/displayed for visitors pointing to `http://<server-ip>:3000`
- [ ] Admin password has been changed from the default
- [ ] Test a message submission end-to-end
- [ ] Verify moderation delay works (messages appear after ~1 minute)

---

## Quick Reference

```bash
# Start server (development)
cd ~/ldw && npm start

# Start Pi client (manual, current 2-panel setup)
cd ~/ldw && sudo python3 pi-client/client.py --led-chain=2

# Start Pi client (target 8-panel setup with working bonnet)
cd ~/ldw && sudo python3 pi-client/client.py --led-chain=4 --led-parallel=2

# Check server health
curl http://172.16.155.51:3000/api/v1/health

# View Pi client logs
sudo journalctl -u ldw-display -f

# Restart Pi client
sudo systemctl restart ldw-display

# Update code on Pi (if local changes conflict)
cd ~/ldw && git clean -fd && git checkout -- . && git pull
```
