# LDW LED Wall – Deployment Guide

This project has two parts:
1. **Server** (Node.js) – serves the web form and manages the message queue
2. **Pi Client** (Python) – runs on a Raspberry Pi connected to LED panels, polls the server for messages

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
git clone <repo-url>
cd ldw-web-form-main

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
git clone <repo-url>
cd ldw-web-form-main
npm install

# 4. Create a systemd service for auto-start
sudo tee /etc/systemd/system/ldw-server.service > /dev/null << 'EOF'
[Unit]
Description=LDW LED Wall Message Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/user/ldw-web-form-main
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

### Hardware Requirements

| Component | Details |
|-----------|---------|
| Raspberry Pi | Pi 4 (recommended) or Pi 3B+ |
| LED Panels | 8× HUB75 64×64 RGB LED panels |
| HAT/Bonnet | Adafruit RGB Matrix Bonnet or HAT (recommended) |
| Power Supply | 5V, 40A+ (8 panels × ~4A each at full brightness) |
| Cables | HUB75 ribbon cables (usually included with panels) |
| SD Card | 16GB+ with Raspberry Pi OS Lite |

### Wiring: 8 Panels in 2×4 Layout

```
                   Raspberry Pi + Bonnet
                   ┌─────────────────┐
                   │  GPIO / Bonnet  │
                   │                 │
          Chain 1 ─┤ HUB75 OUT #1   │── Chain 2
                   └─────────────────┘
                          │                    │
    ┌─────────┬─────────┬─────────┬─────────┐  │
    │ Panel 1 │ Panel 2 │ Panel 3 │ Panel 4 │  │  ← Top row (chain 1)
    │  64x64  │  64x64  │  64x64  │  64x64  │  │
    └─────────┴─────────┴─────────┴─────────┘  │
                                                │
    ┌─────────┬─────────┬─────────┬─────────┐  │
    │ Panel 5 │ Panel 6 │ Panel 7 │ Panel 8 │ ◀┘  ← Bottom row (chain 2)
    │  64x64  │  64x64  │  64x64  │  64x64  │
    └─────────┴─────────┴─────────┴─────────┘

    Total resolution: 256 × 128 pixels
```

**How to connect each chain:**
- Each panel has a HUB75 **input** and **output** connector
- Connect Panel 1 **input** to the Bonnet's HUB75 output #1
- Connect Panel 1 **output** → Panel 2 **input** → Panel 2 **output** → Panel 3 **input** → ... → Panel 4
- Repeat for Chain 2 on the Bonnet's HUB75 output #2
- Connect **all panels** to the 5V power supply (do NOT power panels from the Pi!)

### Software Setup on Raspberry Pi

#### 1. Install Raspberry Pi OS Lite

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash **Raspberry Pi OS Lite (64-bit)** to an SD card. Enable SSH during setup.

#### 2. Initial System Setup

```bash
# SSH into the Pi
ssh pi@raspberrypi.local

# Update system
sudo apt update && sudo apt upgrade -y

# Install build tools and Python
sudo apt install -y python3 python3-pip git
```

#### 3. Install rpi-rgb-led-matrix Library

```bash
cd ~
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix

# Install build dependencies
sudo apt install -y cmake python3-dev cython3 python3-pil
sudo pip3 install pillow --break-system-packages

# Build and install Python bindings
sudo pip3 install . --break-system-packages
```

#### 4. Disable On-Board Sound (Important!)

The on-board sound uses the same GPIO pins as the LED matrix. You must disable it:

```bash
# Add to /boot/config.txt (or /boot/firmware/config.txt on newer OS)
sudo bash -c 'echo "dtparam=audio=off" >> /boot/config.txt'
```

#### 5. Install the Pi Client

```bash
cd ~
git clone <repo-url>
cd ldw-web-form-main/pi-client

# Install Python dependencies
pip3 install -r requirements.txt
```

#### 6. Configure the Client

Edit `config.py`:

```python
# Set to your server's address
SERVER_URL = "http://192.168.1.100:3000"   # local server
# or
SERVER_URL = "https://ldw.example.com"      # VPS

DISPLAY_ID = "pi-01"
DISPLAY_TIME = 10
POLL_INTERVAL = 2
```

#### 7. Test the Display

```bash
# Basic test (must run as root for GPIO access)
sudo python3 client.py \
    --led-rows=64 \
    --led-cols=64 \
    --led-chain=4 \
    --led-parallel=2 \
    --led-hardware-mapping=adafruit-hat \
    --led-slowdown-gpio=4 \
    --led-brightness=80
```

**Troubleshooting the display:**

| Problem | Solution |
|---------|----------|
| Flickering / ghosting | Increase `--led-slowdown-gpio` (try 2, 3, or 4) |
| Wrong colors / garbled | Try `--led-row-addr-type=1` (common for 64×64 panels) |
| Only half the panel lights up | Try different `--led-multiplexing` values (0–18) |
| Panel shows shifted/wrong pixels | Set `--led-panel-type=FM6126A` (if your panels use that chip) |
| Panels in wrong order | Physically re-order the ribbon cables |
| Serpentine layout issues | Add `--led-pixel-mapper="U-mapper"` |

#### 8. Auto-Start on Boot

Create a systemd service so the client starts automatically:

```bash
sudo tee /etc/systemd/system/ldw-display.service > /dev/null << 'EOF'
[Unit]
Description=LDW LED Display Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/ldw-web-form-main/pi-client
ExecStart=/usr/bin/python3 client.py --led-rows=64 --led-cols=64 --led-chain=4 --led-parallel=2 --led-hardware-mapping=adafruit-hat --led-slowdown-gpio=4 --led-brightness=80
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

#### 9. Reboot and Verify

```bash
sudo reboot
# After reboot, check that the display service is running:
sudo systemctl status ldw-display
```

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
npm start

# Start Pi client (manual)
sudo python3 pi-client/client.py --led-rows=64 --led-cols=64 --led-chain=4 --led-parallel=2 --led-slowdown-gpio=4

# Check server health
curl http://localhost:3000/api/v1/health

# View Pi client logs
sudo journalctl -u ldw-display -f

# Restart Pi client
sudo systemctl restart ldw-display
```
