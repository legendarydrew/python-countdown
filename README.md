# MicroPython Pico Countdown Timer (TM1367)

This repo contains a simple countdown timer written for MicroPython on the Raspberry Pi Pico using a 6-digit 7-segment module driven by a TM1367/TM1637-style 2-wire interface.

Files
- display_tm1367.py - TM1367 driver (bit-banged DIO/CLK)
- buzzer.py - PWM buzzer helper
- main.py - main application (button handling, state machine, countdown)
- wiring.md - wiring notes and recommended pinout
- LICENSE - MIT license

Quick start
1. Flash MicroPython to your Pico.
2. Copy the files to the Pico's filesystem (e.g., with Thonny or rshell), ensuring main.py is present.
3. Wire the TM1367 display, buttons, and buzzer as in wiring.md.
4. Reset the Pico. Use the H+/H-/M+/M- buttons to set time, START to begin/pause, RESET to clear.

Notes
- The driver uses conservative timing; if your display is dim or flickers, try reducing clk_delay_us in display_tm1367.TM1367.
- Button logic assumes active-low switches to ground and use of internal pull-ups. Change wiring or code if you prefer external pull-downs.
