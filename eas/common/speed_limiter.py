# -*- coding: utf-8 -*-

import time

__all__ = ["SpeedLimiter"]

class Sleeper(object):
    def __init__(self):
        self._time_wasted = 0.0

    def sleep(self, duration):
        t1 = time.monotonic()

        if duration > self._time_wasted:
            time.sleep(duration - self._time_wasted)

        t2 = time.monotonic()

        self._time_wasted += t2 - t1 - duration

class SpeedLimiter(object):
    def __init__(self, limit=float("inf"), interval=1.0):
        self._quantity = 0
        self.limit = limit
        self.interval = interval
        self._last_delay = time.monotonic()
        self._sleeper = Sleeper()

    def begin(self):
        self._last_delay = time.monotonic()

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        self._quantity = value

    def sleep(self, duration):
        self._sleeper.sleep(duration)

    def delay(self):
        if self.limit is not None and self._quantity < self.limit * self.interval:
            return

        dt = min(time.monotonic() - self._last_delay, self.interval)

        sleep_duration = self._quantity / self.limit - dt

        if sleep_duration > 0.0:
            self.sleep(sleep_duration)

        self._quantity = 0
        self._last_delay = time.monotonic()
