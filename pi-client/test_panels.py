#!/usr/bin/env python3
"""Quick test: fill all panels with color for 60 seconds.

Usage:
  sudo python3 test_panels.py
  sudo python3 test_panels.py --led-panel-type=FM6126A
  sudo python3 test_panels.py --led-row-addr-type=1
  sudo python3 test_panels.py --led-multiplexing=1
  sudo python3 test_panels.py --led-chain=1
"""
import sys
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 2
options.parallel = 1
options.hardware_mapping = 'regular'
options.gpio_slowdown = 4

# Parse extra flags
for arg in sys.argv[1:]:
    if arg.startswith('--led-panel-type='):
        options.panel_type = arg.split('=')[1]
    elif arg.startswith('--led-row-addr-type='):
        options.row_address_type = int(arg.split('=')[1])
    elif arg.startswith('--led-multiplexing='):
        options.multiplexing = int(arg.split('=')[1])
    elif arg.startswith('--led-chain='):
        options.chain_length = int(arg.split('=')[1])
    elif arg.startswith('--led-slowdown-gpio='):
        options.gpio_slowdown = int(arg.split('=')[1])
    elif arg.startswith('--led-rows='):
        options.rows = int(arg.split('=')[1])
    elif arg.startswith('--led-cols='):
        options.cols = int(arg.split('=')[1])

print(f"Config: {options.cols}x{options.rows}, chain={options.chain_length}, parallel={options.parallel}")
matrix = RGBMatrix(options=options)

# Fill entire display with solid colors using Fill()
for r, g, b, label in [(255,0,0,"RED"), (0,255,0,"GREEN"), (0,0,255,"BLUE")]:
    print(f"{label} for 20s...")
    matrix.Fill(r, g, b)
    time.sleep(20)

print("Done.")
matrix.Clear()
