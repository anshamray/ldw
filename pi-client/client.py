#!/usr/bin/env python3
"""
LED Display Client for Raspberry Pi
Polls the server for messages and displays them on the LED matrix
using the rpi-rgb-led-matrix library.

Usage:
    sudo python client.py [matrix options]

    Example with common options:
    sudo python client.py --led-rows=32 --led-cols=64 --led-slowdown-gpio=4

Configure server settings in config.py
For matrix options, run: python client.py --help

Requires:
    - rpi-rgb-led-matrix library: https://github.com/hzeller/rpi-rgb-led-matrix
    - requests library: pip install requests
"""

import requests
import time
import sys
import os
from datetime import datetime

# Add rpi-rgb-led-matrix library path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from config import SERVER_URL, DISPLAY_ID, DISPLAY_TIME, POLL_INTERVAL, SCROLL_END_PAUSE

# Try to import LED matrix library (only available on Raspberry Pi)
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    LED_MATRIX_AVAILABLE = True
except ImportError:
    LED_MATRIX_AVAILABLE = False
    print("WARNING: rgbmatrix not available. Running in console-only mode.")
    print("On Raspberry Pi, install from: https://github.com/hzeller/rpi-rgb-led-matrix")
    print("")


def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


class LEDDisplay:
    """Handles LED matrix display using rpi-rgb-led-matrix library."""

    def __init__(self, args=None):
        self.matrix = None
        self.canvas = None
        self.font = None
        self.text_color = None

        if LED_MATRIX_AVAILABLE:
            self._init_matrix(args)

    def _init_matrix(self, args):
        """Initialize the RGB LED matrix."""
        options = RGBMatrixOptions()

        # Defaults for 64x64 panels with Adafruit Bonnet on Pi 4
        options.rows = 64
        options.cols = 64
        options.chain_length = 2
        options.parallel = 1
        options.hardware_mapping = 'regular'
        options.gpio_slowdown = 4

        # Parse command line args for matrix options
        if args:
            for arg in args:
                if arg.startswith('--led-rows='):
                    options.rows = int(arg.split('=')[1])
                elif arg.startswith('--led-cols='):
                    options.cols = int(arg.split('=')[1])
                elif arg.startswith('--led-chain='):
                    options.chain_length = int(arg.split('=')[1])
                elif arg.startswith('--led-parallel='):
                    options.parallel = int(arg.split('=')[1])
                elif arg.startswith('--led-slowdown-gpio='):
                    options.gpio_slowdown = int(arg.split('=')[1])
                elif arg.startswith('--led-hardware-mapping='):
                    options.hardware_mapping = arg.split('=')[1]
                elif arg.startswith('--led-brightness='):
                    options.brightness = int(arg.split('=')[1])
                elif arg.startswith('--led-row-addr-type='):
                    options.row_address_type = int(arg.split('=')[1])
                elif arg.startswith('--led-multiplexing='):
                    options.multiplexing = int(arg.split('=')[1])
                elif arg.startswith('--led-panel-type='):
                    options.panel_type = arg.split('=')[1]
                elif arg.startswith('--led-pixel-mapper='):
                    options.pixel_mapper_config = arg.split('=')[1]

        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()

        # Total display dimensions
        self.width = options.cols * options.chain_length
        self.height = options.rows * options.parallel

        # Load font sized for display height
        self.font = graphics.Font()
        font_path = self._find_font()
        if font_path:
            self.font.LoadFont(font_path)
            log(f"Loaded font: {font_path}")
        else:
            log("WARNING: Could not find BDF font file")

        # White text by default
        self.text_color = graphics.Color(255, 255, 255)

        # Vertical center for text (font baseline)
        self.text_y = (self.height + self.font.height) // 2

        log(f"Matrix initialized: {self.width}x{self.height} (chain={options.chain_length}, parallel={options.parallel})")

    def _find_font(self):
        """Find a BDF font file. Prefers larger fonts for taller displays."""
        import os
        font_name = "10x20.bdf" if getattr(self, 'height', 64) >= 64 else "6x13.bdf"

        # 0) Check relative to this script's directory (fonts/ subfolder or same dir)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_paths = [
            os.path.join(script_dir, "fonts", font_name),
            os.path.join(script_dir, font_name),
        ]
        for p in local_paths:
            log(f"  Checking local: {p} -> exists={os.path.exists(p)}")
            if os.path.exists(p):
                return p

        # 1) Try well-known hardcoded paths
        hardcoded = [
            f"/home/pi/rpi-rgb-led-matrix/fonts/{font_name}",
            f"/home/pi/rpi-rgb-led-matrix/fonts/6x13.bdf",
            f"/home/pi/rpi-rgb-led-matrix/fonts/9x18.bdf",
        ]
        for p in hardcoded:
            log(f"  Checking hardcoded: {p} -> exists={os.path.exists(p)}")
            if os.path.exists(p):
                return p

        # 2) Use subprocess to find fonts (os.walk can miss things with sudo)
        import subprocess
        try:
            result = subprocess.run(
                ["find", "/home", "/usr", "-name", "*.bdf", "-type", "f"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
            log(f"  find returned {len(lines)} results: {lines[:5]}")
            if lines:
                # prefer the font_name if found
                for l in lines:
                    if l.endswith(font_name):
                        return l
                return lines[0]
        except Exception as e:
            log(f"  find error: {e}")

        log("  No BDF font found anywhere")
        return None

    def scroll_text(self, text, scroll_speed=0.03):
        """
        Scroll text across the LED matrix.
        Text ALWAYS scrolls completely regardless of time.
        Pauses at the end so viewers can read the final part.
        """
        if not self.matrix:
            # Console fallback
            self._console_display(text)
            return

        canvas = self.canvas
        pos = canvas.width
        y = self.text_y

        # Calculate text width
        text_len = len(text) * self.font.CharacterWidth(ord('A'))

        # Scroll until text is fully visible at left edge, then pause
        while pos > 0:
            canvas.Clear()
            text_len = graphics.DrawText(canvas, self.font, pos, y, self.text_color, text)
            pos -= 1
            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(scroll_speed)

        # Show text at position 0 (left aligned) and pause so viewers can read
        canvas.Clear()
        graphics.DrawText(canvas, self.font, 0, y, self.text_color, text)
        self.matrix.SwapOnVSync(canvas)
        time.sleep(SCROLL_END_PAUSE)

        # Continue scrolling off screen
        while pos + text_len > 0:
            canvas.Clear()
            text_len = graphics.DrawText(canvas, self.font, pos, y, self.text_color, text)
            pos -= 1
            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(scroll_speed)

    def static_text(self, text, duration):
        """
        Display static text for a duration.
        Text will be centered if it fits, scrolled once if it doesn't.
        """
        if not self.matrix:
            self._console_display(text)
            time.sleep(duration)
            return

        char_width = self.font.CharacterWidth(ord('A'))
        text_len = len(text) * char_width

        if text_len <= self.canvas.width:
            # Text fits - display centered
            canvas = self.canvas
            canvas.Clear()
            x_pos = (canvas.width - text_len) // 2
            graphics.DrawText(canvas, self.font, x_pos, self.text_y, self.text_color, text)
            self.matrix.SwapOnVSync(canvas)
            time.sleep(duration)
        else:
            # Text doesn't fit - scroll it
            self.scroll_text(text)

    def clear(self):
        """Clear the display."""
        if self.matrix:
            self.canvas.Clear()
            self.matrix.SwapOnVSync(self.canvas)

    def _console_display(self, text):
        """Fallback display for non-Pi environments."""
        print("")
        print("=" * 50)
        print(f"  {text}")
        print("=" * 50)
        print("")


class MessageClient:
    """Handles communication with the message server."""

    def __init__(self):
        self.server_url = SERVER_URL
        self.display_id = DISPLAY_ID

    def get_next_message(self):
        """Fetch the next message from the server queue."""
        try:
            response = requests.get(
                f"{self.server_url}/api/v1/messages/next",
                params={"displayId": self.display_id},
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return None
            else:
                log(f"Unexpected status: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            log(f"Connection error: {e}")
            return None

    def acknowledge_displayed(self, message_id):
        """Tell the server that a message has been displayed."""
        try:
            response = requests.post(
                f"{self.server_url}/api/v1/messages/{message_id}/displayed",
                json={"displayId": self.display_id},
                timeout=10
            )
            return response.status_code == 200

        except requests.exceptions.RequestException as e:
            log(f"Error acknowledging message: {e}")
            return False

    def check_health(self):
        """Check if the server is reachable."""
        try:
            response = requests.get(
                f"{self.server_url}/api/v1/health",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                log(f"Server healthy. Queue size: {data.get('queueSize', 'unknown')}")
                return True
            return False

        except requests.exceptions.RequestException:
            return False


def print_help():
    """Print usage information."""
    print("""
LED Display Client for Raspberry Pi

Usage: sudo python client.py [options]

Server options (configure in config.py):
    SERVER_URL      - URL of the message server
    DISPLAY_ID      - Unique ID for this display
    DISPLAY_TIME    - Seconds to show each message
    POLL_INTERVAL   - Seconds between polls when queue empty

LED Matrix options:
    --led-rows=N           Rows per panel (default: 64)
    --led-cols=N           Columns per panel (default: 64)
    --led-chain=N          Number of chained panels (default: 2)
    --led-parallel=N       Parallel chains (default: 1)
    --led-slowdown-gpio=N  GPIO slowdown (try 2-4 for Pi 4)
    --led-brightness=N     Brightness 1-100 (default: 100)
    --led-hardware-mapping=TYPE  Hardware mapping (regular, adafruit-hat, adafruit-hat-pwm)
    --led-row-addr-type=N  Row address type (0-4, try 1 for 64x64 panels)
    --led-multiplexing=N   Multiplexing type (0-18, panel-dependent)
    --led-panel-type=TYPE  Panel type (e.g. FM6126A)
    --led-pixel-mapper=MAP Pixel mapper (e.g. "U-mapper" for serpentine layout)

Example (8x 64x64 panels, 2 parallel chains of 4, Adafruit HAT):
    sudo python client.py --led-rows=64 --led-cols=64 --led-chain=4 \\
        --led-parallel=2 --led-hardware-mapping=adafruit-hat \\
        --led-slowdown-gpio=4 --led-brightness=80
""")


def main():
    """Main polling loop."""
    args = sys.argv[1:]

    if '--help' in args or '-h' in args:
        print_help()
        sys.exit(0)

    log("LED Display Client starting...")
    log(f"Server: {SERVER_URL}")
    log(f"Display ID: {DISPLAY_ID}")
    log(f"Display time: {DISPLAY_TIME}s")
    log(f"Poll interval: {POLL_INTERVAL}s")
    print("")

    # Initialize LED display
    display = LEDDisplay(args)

    # Initialize message client
    client = MessageClient()

    # Check server connection
    log("Checking server connection...")
    if not client.check_health():
        log("WARNING: Cannot reach server. Will keep trying...")
    else:
        log("Server connection OK!")

    print("")
    log("Entering main loop. Press Ctrl+C to stop.")
    print("")

    try:
        while True:
            message = client.get_next_message()

            if message:
                text = message.get("text", "")
                message_id = message.get("messageId", "")
                is_default = message.get("isDefault", False)

                if is_default:
                    log(f"Showing default phrase")
                else:
                    log(f"Received message: {message_id}")
                log(f"Text: {text}")

                # Display on LED matrix
                display.static_text(text, DISPLAY_TIME)

                # Acknowledge displayed (for non-default messages)
                if client.acknowledge_displayed(message_id):
                    if not is_default:
                        log(f"Acknowledged: {message_id}")
                else:
                    log(f"Failed to acknowledge: {message_id}")

                display.clear()

            else:
                # No message, wait before polling again
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("")
        log("Shutting down...")
        display.clear()
        sys.exit(0)


if __name__ == "__main__":
    main()
