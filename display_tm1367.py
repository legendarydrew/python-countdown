"""
TM1367 / TM1637-like driver for MicroPython on Raspberry Pi Pico
Supports up to 6 digits. Bit-banged CLK/DIO interface.

Usage:
    from display_tm1367 import TM1367
    disp = TM1367(clk_pin=1, dio_pin=0, brightness=4)
    disp.show([1,2,3,4,5,6])
    disp.show_time(h=1, m=23, s=45)

This driver is intentionally small and conservative in timing to work on Pico.
"""

from machine import Pin
import time

# Segment byte maps for common 7-seg (0-9, A-F, dash, blank)
_DIGIT_MAP = {
    0: 0x3f,
    1: 0x06,
    2: 0x5b,
    3: 0x4f,
    4: 0x66,
    5: 0x6d,
    6: 0x7d,
    7: 0x07,
    8: 0x7f,
    9: 0x6f,
    ' ': 0x00,
    '-': 0x40,
}

class TM1367:
    def __init__(self, clk_pin, dio_pin, brightness=7, clk_delay_us=5):
        self.clk = Pin(clk_pin, Pin.OUT)
        self.dio = Pin(dio_pin, Pin.OUT)
        self.brightness = max(0, min(7, brightness))
        self.clk_delay_us = clk_delay_us
        # initial idle state
        self.clk.value(1)
        self.dio.value(1)

    def _usleep(self, us):
        # time.sleep_us can be coarse on some builds, keep it small
        time.sleep_us(us)

    def _start(self):
        self.dio.value(1)
        self.clk.value(1)
        self._usleep(self.clk_delay_us)
        self.dio.value(0)
        self._usleep(self.clk_delay_us)
        self.clk.value(0)
        self._usleep(self.clk_delay_us)

    def _stop(self):
        self.clk.value(0)
        self._usleep(self.clk_delay_us)
        self.dio.value(0)
        self._usleep(self.clk_delay_us)
        self.clk.value(1)
        self._usleep(self.clk_delay_us)
        self.dio.value(1)
        self._usleep(self.clk_delay_us)

    def _write_byte(self, b):
        for i in range(8):
            self.clk.value(0)
            bit = (b >> i) & 1
            self.dio.value(bit)
            self._usleep(self.clk_delay_us)
            self.clk.value(1)
            self._usleep(self.clk_delay_us)
        # ack
        self.clk.value(0)
        self.dio.init(Pin.IN)
        self._usleep(self.clk_delay_us)
        self.clk.value(1)
        self._usleep(self.clk_delay_us)
        # read ack (ignored if device doesn't drive)
        try:
            ack = self.dio.value()
        except Exception:
            ack = 1
        self.clk.value(0)
        self.dio.init(Pin.OUT)
        return ack

    def set_brightness(self, level):
        self.brightness = max(0, min(7, level))

    def _encode_digit(self, v):
        if isinstance(v, int):
            return _DIGIT_MAP.get(v, 0x00)
        return _DIGIT_MAP.get(v, 0x00)

    def show_raw(self, seg_bytes):
        """Send 6 raw segment bytes to the display (LSB/segment mapping as in map).
        seg_bytes: iterable of length 6
        """
        if len(seg_bytes) != 6:
            raise ValueError("seg_bytes must be length 6")
        # command1: automatic address increment
        self._start()
        self._write_byte(0x40)
        self._stop()
        # command2: set start address to 0x00
        self._start()
        self._write_byte(0xC0)
        for b in seg_bytes:
            self._write_byte(b)
        self._stop()
        # command3: display control: 0x88 | brightness
        self._start()
        self._write_byte(0x88 | self.brightness)
        self._stop()

    def show(self, digits):
        """digits: list/tuple of 6 values (int 0-9, ' ' or '-')
        """
        segs = []
        for d in digits:
            segs.append(self._encode_digit(d))
        self.show_raw(segs)

    def show_time(self, h=0, m=0, s=0):
        # clamp hours to 99
        h = max(0, min(99, int(h)))
        m = max(0, min(59, int(m)))
        s = max(0, min(59, int(s)))
        h1 = h // 10
        h2 = h % 10
        m1 = m // 10
        m2 = m % 10
        s1 = s // 10
        s2 = s % 10
        self.show([h1, h2, m1, m2, s1, s2])
