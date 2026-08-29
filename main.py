"""
Main application for the Pico countdown timer.

Pin mapping and display options are sourced from config.py so settings are shared
with test_buttons.py.
"""
from machine import Pin
import time
import ujson
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

    def is_pressed(self, name):
        """Return True if button "name" is currently pressed (active-low)."""
        return self.stable_state.get(name, 1) == 0

# utility
def secs_from_hms(h, m, s):
    return h*3600 + m*60 + s

# Persistence helpers
def load_last_set():
    try:
        with open(PERSIST_FILE, 'r') as f:
            data = ujson.loads(f.read())
            h = int(data.get('h', 0))
            m = int(data.get('m', 1))
            s = int(data.get('s', 0))
            return {'h': max(0, min(99, h)), 'm': max(0, min(59, m)), 's': max(0, min(59, s))}
    except Exception:
        return {'h': 0, 'm': 1, 's': 0}

def save_last_set(s):
    try:
        with open(PERSIST_FILE, 'w') as f:
            f.write(ujson.dumps(s))
    except Exception:
        # ignore write errors
        pass

# Setup
display = TM1367(clk_pin=CLK_PIN, dio_pin=DIO_PIN, brightness=config.DISPLAY_BRIGHTNESS, reverse_groups=config.REVERSE_DISPLAY)
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
last_set = load_last_set()  # persisted
remaining = secs_from_hms(**last_set)
last_tick = time.ticks_ms()

# hold/auto-repeat info for set buttons
_hold_info = {
    'H+': {'pressed': False, 'start': 0, 'last': 0, 'initial_delay': config.HOLD_INITIAL_DELAY_MS, 'repeat_ms': config.HOLD_REPEAT_MS},
    'H-': {'pressed': False, 'start': 0, 'last': 0, 'initial_delay': config.HOLD_INITIAL_DELAY_MS, 'repeat_ms': config.HOLD_REPEAT_MS},
    'M+': {'pressed': False, 'start': 0, 'last': 0, 'initial_delay': config.HOLD_INITIAL_DELAY_MS, 'repeat_ms': config.HOLD_REPEAT_MS},
    'M-': {'pressed': False, 'start': 0, 'last': 0, 'initial_delay': config.HOLD_INITIAL_DELAY_MS, 'repeat_ms': config.HOLD_REPEAT_MS},
}

# persistence throttle: save PERSIST_DELAY_MS after last change
_last_set_dirty = False
_last_set_changed_ts = 0

print('Countdown started. Use buttons to set time and start. Loaded last_set:', last_set)

# helper to update display
def update_display_from_remaining(rem):
    rem = max(0, int(rem))
    h = rem // 3600
    m = (rem % 3600) // 60
    s = rem % 60
    # create dots pattern: blink colon separators every second
    dot_on = (s % 2) == 0
    # enable DP on digit positions 1 and 3 (after h2 and m2)
    dots = [False, dot_on, False, dot_on, False, False]
    display.show_time(h=h, m=m, s=s, dots=dots, suppress_leading=True)

# main loop
_alarm_pattern = [(1000, 150), (0, 100), (1500, 200), (0, 120)]  # (freq, ms) where freq=0 means silence
_alarm_index = 0
_alarm_step_ts = 0

while True:
    now = time.ticks_ms()
    # poll buttons
    evts = buttons.poll()

    # handle events
    changed = False
    for ev_type, name in evts:
        if ev_type == 'pressed':
            # beep on press
            try:
                buzzer.beep(config.BUTTON_BEEP_FREQ, config.BUTTON_BEEP_MS)
            except Exception:
                pass
            # set hold info
            if name in _hold_info:
                hi = _hold_info[name]
                hi['pressed'] = True
                hi['start'] = now
                hi['last'] = now
            # immediate action on press
            if name == 'H+':
                if state != 'running':
                    last_set['h'] = min(99, last_set['h'] + 1)
                    remaining = secs_from_hms(**last_set)
                    changed = True
            elif name == 'H-':
                if state != 'running':
                    last_set['h'] = max(0, last_set['h'] - 1)
                    remaining = secs_from_hms(**last_set)
                    changed = True
            elif name == 'M+':
                if state != 'running':
                    last_set['m'] = min(59, last_set['m'] + 1)
                    remaining = secs_from_hms(**last_set)
                    changed = True
            elif name == 'M-':
                if state != 'running':
                    last_set['m'] = max(0, last_set['m'] - 1)
                    remaining = secs_from_hms(**last_set)
                    changed = True
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
                        last_tick = now
        elif ev_type == 'released':
            # release hold info
            if name in _hold_info:
                hi = _hold_info[name]
                hi['pressed'] = False
                hi['start'] = 0
                hi['last'] = 0

    # auto-repeat handling for held set buttons (only when not running)
    if state != 'running':
        for name, hi in _hold_info.items():
            if hi['pressed']:
                elapsed = time.ticks_diff(now, hi['start'])
                # if elapsed >= initial_delay, start repeating
                if elapsed >= hi['initial_delay']:
                    # if this is first repeat or enough time since last repeat
                    if hi['last'] == hi['start'] or time.ticks_diff(now, hi['last']) >= hi['repeat_ms']:
                        # perform action
                        if name == 'H+':
                            last_set['h'] = min(99, last_set['h'] + 1)
                        elif name == 'H-':
                            last_set['h'] = max(0, last_set['h'] - 1)
                        elif name == 'M+':
                            last_set['m'] = min(59, last_set['m'] + 1)
                        elif name == 'M-':
                            last_set['m'] = max(0, last_set['m'] - 1)
                        remaining = secs_from_hms(**last_set)
                        hi['last'] = now
                        changed = True

    # mark dirty when changed (defer saving to reduce flash wear)
    if changed:
        _last_set_dirty = True
        _last_set_changed_ts = now

    # persist if dirty and PERSIST_DELAY_MS elapsed since last change
    if _last_set_dirty and time.ticks_diff(now, _last_set_changed_ts) >= config.PERSIST_DELAY_MS:
        save_last_set(last_set)
        _last_set_dirty = False
        _last_set_changed_ts = 0

    # running logic: decrement once per second
    if state == 'running':
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
        if _alarm_step_ts == 0:
            _alarm_step_ts = now
        freq, dur = _alarm_pattern[_alarm_index]
        if time.ticks_diff(now, _alarm_step_ts) >= dur:
            _alarm_index = (_alarm_index + 1) % len(_alarm_pattern)
            _alarm_step_ts = now
            freq, dur = _alarm_pattern[_alarm_index]
            if freq > 0:
                try:
                    buzzer._start_tone(freq)
                except Exception:
                    pass
            else:
                try:
                    buzzer._stop_tone()
                except Exception:
                    pass
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
