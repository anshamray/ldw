#!/usr/bin/env python3
"""Quick test: fill all panels with color for 60 seconds."""
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 2
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'
options.gpio_slowdown = 4

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# Fill red for 20s, green for 20s, blue for 20s
for color, label in [((255,0,0), "RED"), ((0,255,0), "GREEN"), ((0,0,255), "BLUE")]:
    print(f"{label} - all pixels for 20s...")
    for x in range(canvas.width):
        for y in range(canvas.height):
            canvas.SetPixel(x, y, *color)
    matrix.SwapOnVSync(canvas)
    time.sleep(20)

print("Done.")
matrix.Clear()
