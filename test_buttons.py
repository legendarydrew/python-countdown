"""
Button wiring test for Pico countdown project.

Run this on the Pico (REPL or as main module) to verify your buttons are wired correctly.
It polls the buttons with simple debounce logic and prints events when buttons
are pressed or released. It also tries to play a short beep on press if the
buzzer.py helper is present.

Default pins (match wiring.md / main.py):
- H+ -> GP14
- H- -> GP15
- M+ -> GP16
- M- -> GP17
- RESET -> GP18
- START -> GP19

Usage:
- Copy to the Pico and run `import test_buttons` or `python test_buttons.py`.
- Press each button and watch the REPL for "pressed <name>" and "released <name>" lines.

"""
from machine import Pin
import time

# default pin mapping (change if you wired differently)
BUTTON_H_UP = 14
BUTTON_H_DOWN = 15
BUTTON_M_UP = 16
BUTTON_M_DOWN = 17
BUTTON_RESET = 18
BUTTON_START = 19
BUZZ_PIN = 20

_DEBOUNCE_MS = 40

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

    print('Button test started. Press each button and watch for events.')
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
            # optional: every second print a compact state summary
            # (helps verify pull-ups / stuck pins). Not too chatty.
            time.sleep_ms(30)
    except KeyboardInterrupt:
        print('Test stopped by user')


if __name__ == '__main__':
    main()
