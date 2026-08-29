"""
Button wiring test for Pico countdown project.

Imports configuration from config.py and writes " TEST " to the TM1367 display.
Run this on the Pico (REPL or as main module) to verify your buttons are wired correctly.
"""
from machine import Pin
import time
from display_tm1367 import TM1367
import config

# Read pins from shared config
BUTTON_H_UP = config.BUTTON_H_UP
BUTTON_H_DOWN = config.BUTTON_H_DOWN
BUTTON_M_UP = config.BUTTON_M_UP
BUTTON_M_DOWN = config.BUTTON_M_DOWN
BUTTON_RESET = config.BUTTON_RESET
BUTTON_START = config.BUTTON_START
BUZZ_PIN = config.BUZZ_PIN

_DEBOUNCE_MS = config.DEBOUNCE_MS

class DebouncedButtons:
    def __init__(self, pin_map):
        self.pins = {}
        self.last_raw = {}
        self.stable_state = {}
        self.last_change = {}
        for name, pno in pin_map.items():
            p = Pin(pno, Pin.IN, Pin.PULL_UP)
            self.pins[name] = p
            val = p.value()
            self.last_raw[name] = val
            self.stable_state[name] = val
            self.last_change[name] = time.ticks_ms()

    def poll(self):
        """Return list of events like ('pressed', name) or ('released', name)."""
        events = []
        now = time.ticks_ms()
        for name, p in self.pins.items():
            v = p.value()
            if v != self.last_raw[name]:
                self.last_raw[name] = v
                self.last_change[name] = now
            else:
                if time.ticks_diff(now, self.last_change[name]) >= _DEBOUNCE_MS:
                    if v != self.stable_state[name]:
                        prev = self.stable_state[name]
                        self.stable_state[name] = v
                        # active-low: 0 means pressed
                        if prev == 1 and v == 0:
                            events.append(('pressed', name))
                        elif prev == 0 and v == 1:
                            events.append(('released', name))
        return events

def try_init_buzzer(pin_no):
    try:
        from buzzer import Buzzer
        return Buzzer(pin_no)
    except Exception:
        return None

def main():
    # Initialize display (assume available)
    display = TM1367(clk_pin=config.CLK_PIN, dio_pin=config.DIO_PIN, brightness=config.DISPLAY_BRIGHTNESS)

    # Prepare segment bytes for " TEST " on a 6-digit 7-seg:
    # T = 0x78, E = 0x79, S = 0x6d, blank = 0x00
    segs = [0x00, 0x78, 0x79, 0x6d, 0x78, 0x00]
    try:
        display.show_raw(segs)
    except Exception:
        # If display isn't actually connected this will simply fail; test still runs.
        pass

    button_map = {
        'H+': BUTTON_H_UP,
        'H-': BUTTON_H_DOWN,
        'M+': BUTTON_M_UP,
        'M-': BUTTON_M_DOWN,
        'RESET': BUTTON_RESET,
        'START': BUTTON_START,
    }

    buttons = DebouncedButtons(button_map)
    buzzer = try_init_buzzer(BUZZ_PIN)

    print('Button test started. Display shows \" TEST \". Press each button and watch for events.')
    if buzzer:
        print('Buzzer available: will beep on press.')

    try:
        while True:
            evts = buttons.poll()
            for ev_type, name in evts:
                ts = time.ticks_ms()
                if ev_type == 'pressed':
                    print("{:>7}ms - pressed  {}".format(ts, name))
                    if buzzer:
                        try:
                            buzzer.beep(1500, 60)
                        except Exception:
                            pass
                else:
                    print("{:>7}ms - released {}".format(ts, name))
            time.sleep_ms(30)
    except KeyboardInterrupt:
        print('Test stopped by user')

if __name__ == '__main__':
    main()