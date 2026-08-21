# Wiring

Suggested pin mapping (change in main.py if you prefer different pins):

- TM1367 module
  - VCC -> 3V3
  - GND -> GND
  - DIO -> GP0 (DIO_PIN)
  - CLK -> GP1 (CLK_PIN)

- Buttons (wired to ground; use internal pull-ups)
  - H+ -> GP14
  - H- -> GP15
  - M+ -> GP16
  - M- -> GP17
  - RESET -> GP18
  - START/STOP -> GP19

- Buzzer
  - BUZ -> GP20 (through a transistor if using passive piezo)

Notes
- The TM1367/TM1637 segments draw significant current when multiple segments light; use appropriate resistors or a display module that already includes resistors.
- Drive digit commons through transistors if necessary; the Pico's GPIOs should not be used to source large segment currents directly.
