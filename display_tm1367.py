"""
TM1367 / TM1637-like driver for MicroPython on Raspberry Pi Pico
Supports up to 6 digits. Bit-banged CLK/DIO interface.

Features added:
- Optional DP/dot support per-digit (DP uses MSB 0x80)
- Optional per-group reversal (useful for mirrored 3-digit modules)
- Leading-zero suppression when using show_time()

Usage:
    from display_tm1367 import TM1367
    disp = TM1367(clk_pin=1, dio_pin=0, brightness=4, reverse_groups=True)
    disp.show_time(h=1, m=2, s=3)  # shows 1:02:03 with leading zeros suppressed
    disp.show_time(h=12, m=34, s=56, dots=[False,True,False,True,False,False])

This driver is intentionally small and conservative in timing to work on Pico.
"""

from machine import Pin
import time

# Segment byte maps for common 7-seg (0-9, blank, dash). DP (dot) is the MSB 0x80 and is ORed on demand.
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

DP_BIT = 0x80

class TM1367:
    def __init__(self, clk_pin, dio_pin, brightness=7, clk_delay_us=5, reverse_groups=False, group_size=3):
        self.clk = Pin(clk_pin, Pin.OUT)
        self.dio = Pin(dio_pin, Pin.OUT)
        self.brightness = max(0, min(7, brightness))
        self.clk_delay_us = clk_delay_us
        self.reverse_groups = reverse_groups
        self.group_size = group_size
        # initial idle state
        self.clk.value(1)
        self.dio.value(1)

    def _usleep(self, us):
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

    def _reorder_for_hardware(self, seg_list):
        """Reorder the logical seg_list into the physical order expected by hardware.
        If reverse_groups is True, each group of size group_size is reversed.
        """
        if not self.reverse_groups or self.group_size <= 1:
            return list(seg_list)
        out = []
        n = len(seg_list)
        for i in range(0, n, self.group_size):
            group = seg_list[i:i + self.group_size]
            out.extend(list(reversed(group)))
        return out

    def show_raw(self, seg_bytes):
        """Send 6 raw segment bytes to the display (LSB/segment mapping as in map).
        seg_bytes: iterable of length 6 (each byte is segments, DP as MSB 0x80 when desired)
        """
        if len(seg_bytes) != 6:
            raise ValueError("seg_bytes must be length 6")
        segs_phys = self._reorder_for_hardware(seg_bytes)
        # command1: automatic address increment
        self._start()
        self._write_byte(0x40)
        self._stop()
        # command2: set start address to 0x00
        self._start()
        self._write_byte(0xC0)
        for b in segs_phys:
            self._write_byte(b)
        self._stop()
        # command3: display control: 0x88 | brightness
        self._start()
        self._write_byte(0x88 | self.brightness)
        self._stop()

    def show(self, digits, dots=None):
        """digits: list/tuple of 6 values (int 0-9, ' ' or '-')
           dots: optional iterable of 6 booleans indicating DP on each digit
        """
        if len(digits) != 6:
            raise ValueError("digits must be length 6")
        if dots is None:
            dots = [False] * 6
        segs = []
        for d, dot in zip(digits, dots):
            seg = self._encode_digit(d)
            if dot:
                seg |= DP_BIT
            segs.append(seg)
        self.show_raw(segs)

    def show_time(self, h=0, m=0, s=0, dots=None, suppress_leading=True):
        """Show time as HH:MM:SS with optional dots and leading-zero suppression.
        Leading-zero suppression rules:
          - Do not display the hours tens digit if hours < 10.
          - Do not display the minutes tens if hours == 0 and minutes < 10.
          - Do not display the seconds tens if hours == 0 and minutes == 0 and seconds < 10.
        dots: optional iterable of 6 booleans to enable DP on each digit. If None, no dots.
        """
        h = max(0, min(99, int(h)))
        m = max(0, min(59, int(m)))
        s = max(0, min(59, int(s)))
        digits = [None] * 6
        digits[0] = h // 10
        digits[1] = h % 10
        digits[2] = m // 10
        digits[3] = m % 10
        digits[4] = s // 10
        digits[5] = s % 10

        # apply suppression to create blanks
        if suppress_leading:
            # hours tens
            if h < 10:
                digits[0] = ' '
            if h == 0:
                digits[1] = ' '
            # minutes tens
            if h == 0 and m < 10:
                digits[2] = ' '
            if h == 0 and m == 0:
                digits[3] = ' '
            # seconds tens
            if h == 0 and m == 0 and s < 10:
                digits[4] = ' '

        if dots is None:
            dots = [False] * 6

        self.show(digits, dots=dots)
