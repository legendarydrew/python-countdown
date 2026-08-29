"""
Shared configuration for pin mapping and display options.

Edit these values to match your wiring. Both main.py and test_buttons.py import
from this module so changes apply to both scripts.
"""

# TM1367 pins
CLK_PIN = 1
DIO_PIN = 0

# Buttons (wired to ground; internal pull-ups used)
BUTTON_H_UP = 14
BUTTON_H_DOWN = 15
BUTTON_M_UP = 16
BUTTON_M_DOWN = 17
BUTTON_RESET = 18
BUTTON_START = 19

# Buzzer pin
BUZZ_PIN = 20

# Debounce (ms)
DEBOUNCE_MS = 40

# Display brightness (0-7)
DISPLAY_BRIGHTNESS = 4
