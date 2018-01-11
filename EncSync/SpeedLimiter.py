# -*- coding: utf-8 -*-

import time

__all__ = ["SpeedLimiter"]

class SpeedLimiter(object):
    def __init__(self, limit=float("inf"), interval=1.0):
        self._quantity = 0
        self.limit = limit
        self.interval = interval
        self._last_delay = time.time()

    def begin(self):
        self._last_delay = time.time()

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        self._quantity = value

    def sleep(self, duration):
        time.sleep(duration)

    def delay(self):
        dt = min(time.time() - self._last_delay, self.interval)

        sleep_duration = self._quantity / self.limit - dt

        if sleep_duration > 0.0:
            self.sleep(sleep_duration)

        self._quantity = 0
        self._last_delay = time.time()
