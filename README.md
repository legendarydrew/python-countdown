# MicroPython Pico Countdown Timer (TM1367)

This repo contains a simple countdown timer written for MicroPython on the Raspberry Pi Pico using a 6-digit 7-segment module driven by a TM1367/TM1637-style 2-wire interface.

Files
- display_tm1367.py - TM1367 driver (bit-banged DIO/CLK) with DP/dot support, group reversal and leading-zero suppression
- buzzer.py - PWM buzzer helper
- main.py - main application (button handling, state machine, countdown). Instantiates display with reverse_groups=True for mirrored 3-digit modules.
- wiring.md - suggested pin mapping and wiring notes for Pico + TM1367 + buttons + buzzer.
- LICENSE - MIT license

Quick start
1. Flash MicroPython to your Pico.
2. Copy the files to the Pico's filesystem (e.g., with Thonny or rshell), ensuring main.py is present.
3. Wire the TM1367 display, buttons, and buzzer as in wiring.md.
4. Reset the Pico. Use H+/H-/M+/M- to set time, START to begin/pause, RESET to clear.

New features / notes
- Dot/DP support: show_time accepts a dots= iterable (6 booleans) to turn on decimal points per digit. The main app blinks the colon dots between HH:MM and MM:SS each second.
- Mirrored 3-digit modules: The TM1367 driver supports reversing groups of digits. main.py instantiates the driver with reverse_groups=True and group_size=3 to match two 3-digit modules that present digits in reverse order.
- Leading zero suppression: Hours/minutes/seconds leading zeros are suppressed according to common clock display rules (e.g., 1:02:03 shows as "1:02:03", not "01:02:03").

Notes
- If your hardware has dots mapped to different digits, update main.update_display_from_remaining to set dots on the proper indices.
- The driver uses conservative bit-banging timing; if your display is dim or flickers, try reducing clk_delay_us in display_tm1367.TM1367.
