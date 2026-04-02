#!/usr/bin/env python3
"""Brute-force test: cycles through all combinations of row-addr-type and multiplexing.

Shows solid red for each combo for 4 seconds.
Press Ctrl+C to stop when you see a solid fill (no stripes).

Usage:
  sudo python3 test_panels.py                    # runs brute-force test
  sudo python3 test_panels.py --led-chain=2      # with extra flags
"""
import sys
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def make_options(row_addr_type=0, multiplexing=0, extra_args=None):
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'regular'
    options.gpio_slowdown = 4
    options.row_address_type = row_addr_type
    options.multiplexing = multiplexing

    if extra_args:
        for arg in extra_args:
            if arg.startswith('--led-chain='):
                options.chain_length = int(arg.split('=')[1])
            elif arg.startswith('--led-slowdown-gpio='):
                options.gpio_slowdown = int(arg.split('=')[1])
            elif arg.startswith('--led-rows='):
                options.rows = int(arg.split('=')[1])
            elif arg.startswith('--led-cols='):
                options.cols = int(arg.split('=')[1])
            elif arg.startswith('--led-panel-type='):
                options.panel_type = arg.split('=')[1]
            elif arg.startswith('--led-hardware-mapping='):
                options.hardware_mapping = arg.split('=')[1]
    return options

extra = sys.argv[1:]

print("=" * 60)
print("BRUTE-FORCE PANEL TEST")
print("Testing all row-addr-type (0-5) x multiplexing (0-17)")
print("Each combo shows RED for 4 seconds")
print("Press Ctrl+C when you see SOLID RED (no stripes)")
print("=" * 60)

try:
    for rat in range(6):
        for mux in range(18):
            label = f"row-addr-type={rat}, multiplexing={mux}"
            print(f"\n>>> {label}")
            try:
                options = make_options(rat, mux, extra)
                matrix = RGBMatrix(options=options)
                matrix.Fill(255, 0, 0)
                time.sleep(4)
                matrix.Clear()
                del matrix
                time.sleep(0.5)
            except Exception as e:
                print(f"    ERROR: {e}")
                time.sleep(0.5)
except KeyboardInterrupt:
    print(f"\n\nSTOPPED at: {label}")
    print(f"Use these flags: --led-row-addr-type={rat} --led-multiplexing={mux}")
    try:
        matrix.Clear()
    except:
        pass

print("\nDone.")
