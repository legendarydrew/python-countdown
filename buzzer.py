"""
Simple buzzer helper for Pico using PWM.
Provides blocking beep() and non-blocking start/stop alarm helpers.
"""
from machine import Pin, PWM
import time

class Buzzer:
    def __init__(self, pin_no, duty=512):
        self.pin = Pin(pin_no, Pin.OUT)
        self.pwm = PWM(self.pin)
        self.pwm.deinit()
        self.duty = max(0, min(1023, duty))
        self.alarm_on = False

    def _start_tone(self, freq, duty=None):
        if duty is None:
            duty = self.duty
        self.pwm.init()
        self.pwm.freq(int(freq))
        self.pwm.duty_u16(int(duty * 64))  # scale 0-1023 to 0-65535

    def _stop_tone(self):
        try:
            self.pwm.deinit()
        except Exception:
            pass

    def beep(self, freq=2000, ms=70):
        """Blocking short beep"""
        self._start_tone(freq)
        time.sleep_ms(ms)
        self._stop_tone()

    def alarm_start(self):
        """Non-blocking flag; main loop should produce pattern while alarm_on True"""
        self.alarm_on = True

    def alarm_stop(self):
        self.alarm_on = False
        self._stop_tone()
