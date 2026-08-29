"""
Main application for the Pico countdown timer.

Pin mapping and display options are sourced from config.py so settings are shared
with test_buttons.py.
"""
from machine import Pin
import time
from display_tm1367 import TM1367
from buzzer import Buzzer
import config

# --- Configurable pins (sourced from config.py) ---
CLK_PIN = config.CLK_PIN
DIO_PIN = config.DIO_PIN
BUTTON_H_UP = config.BUTTON_H_UP
BUTTON_H_DOWN = config.BUTTON_H_DOWN
BUTTON_M_UP = config.BUTTON_M_UP
BUTTON_M_DOWN = config.BUTTON_M_DOWN
BUTTON_RESET = config.BUTTON_RESET
BUTTON_START = config.BUTTON_START
BUZZ_PIN = config.BUZZ_PIN

# debounce settings
_DEBOUNCE_MS = config.DEBOUNCE_MS

class DebouncedButtons:
    def __init__(self, pin_map):
        # pin_map: dict name -> pin_no
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
        """Call frequently. Returns list of events like ('pressed', name) when a button goes from high->low."""
        events = []
        now = time.ticks_ms()
        for name, p in self.pins.items():
            v = p.value()
            if v != self.last_raw[name]:
                # raw changed, reset timer
                self.last_raw[name] = v
                self.last_change[name] = now
            else:
                # raw stable since last_change?
                if time.ticks_diff(now, self.last_change[name]) >= _DEBOUNCE_MS:
                    if v != self.stable_state[name]:
                        # stable state changed
                        prev = self.stable_state[name]
                        self.stable_state[name] = v
                        # active-low buttons: pressed when 0
                        if prev == 1 and v == 0:
                            events.append(('pressed', name))
                        elif prev == 0 and v == 1:
                            events.append(('released', name))
        return events

# utility
def secs_from_hms(h, m, s):
    return h*3600 + m*60 + s

# Setup
display = TM1367(clk_pin=CLK_PIN, dio_pin=DIO_PIN, brightness=config.DISPLAY_BRIGHTNESS)
buzzer = Buzzer(BUZZ_PIN)

button_map = {
    'H+': BUTTON_H_UP,
    'H-': BUTTON_H_DOWN,
    'M+': BUTTON_M_UP,
    'M-': BUTTON_M_DOWN,
    'RESET': BUTTON_RESET,
    'START': BUTTON_START,
}
buttons = DebouncedButtons(button_map)

# state
state = 'idle'  # idle, running, alarm
last_set = {'h':0, 'm':1, 's':0}  # default 00:01:00
remaining = secs_from_hms(**last_set)
last_tick = time.ticks_ms()

print('Countdown started. Use buttons to set time and start.')

# helper to update display
def update_display_from_remaining(rem):
    rem = max(0, int(rem))
    h = rem // 3600
    m = (rem % 3600) // 60
    s = rem % 60
    display.show_time(h=h, m=m, s=s)

# main loop
_alarm_pattern = [(1000, 150), (0, 100), (1500, 200), (0, 120)]  # (freq, ms) where freq=0 means silence
_alarm_index = 0
_alarm_step_ts = 0

while True:
    # poll buttons
    evts = buttons.poll()
    for ev_type, name in evts:
        if ev_type == 'pressed':
            # beep on press
            try:
                buzzer.beep(2000, 50)
            except Exception:
                pass
            if name == 'H+':
                if state != 'running':
                    last_set['h'] = min(99, last_set['h'] + 1)
                    remaining = secs_from_hms(**last_set)
            elif name == 'H-':
                if state != 'running':
                    last_set['h'] = max(0, last_set['h'] - 1)
                    remaining = secs_from_hms(**last_set)
            elif name == 'M+':
                if state != 'running':
                    last_set['m'] = min(59, last_set['m'] + 1)
                    remaining = secs_from_hms(**last_set)
            elif name == 'M-':
                if state != 'running':
                    last_set['m'] = max(0, last_set['m'] - 1)
                    remaining = secs_from_hms(**last_set)
            elif name == 'RESET':
                # reset to last_set (or zero)
                remaining = secs_from_hms(**last_set)
                state = 'idle'
                buzzer.alarm_stop()
            elif name == 'START':
                if state == 'running':
                    state = 'idle'
                else:
                    # start only if remaining > 0
                    if remaining > 0:
                        state = 'running'
                        # align tick
                        last_tick = time.ticks_ms()
    # running logic: decrement once per second
    if state == 'running':
        now = time.ticks_ms()
        if time.ticks_diff(now, last_tick) >= 1000:
            last_tick = now
            remaining -= 1
            if remaining <= 0:
                remaining = 0
                state = 'alarm'
                buzzer.alarm_start()
                _alarm_index = 0
                _alarm_step_ts = time.ticks_ms()
    elif state == 'alarm':
        # alarm pattern handled here (non-blocking)
        now = time.ticks_ms()
        freq, dur = _alarm_pattern[_alarm_index]
        if time.ticks_diff(now, _alarm_step_ts) >= dur:
            _alarm_index = (_alarm_index + 1) % len(_alarm_pattern)
            _alarm_step_ts = now
            freq, dur = _alarm_pattern[_alarm_index]
            if freq > 0:
                buzzer._start_tone(freq)
            else:
                buzzer._stop_tone()
        # any button press should silence alarm
        for ev_type, name in evts:
            if ev_type == 'pressed':
                buzzer.alarm_stop()
                state = 'idle'
                remaining = secs_from_hms(**last_set)
                break

    # Update display (fast enough to appear stable)
    update_display_from_remaining(remaining)

    # small sleep to avoid hogging CPU (buttons debounced in software)
    time.sleep_ms(30)
