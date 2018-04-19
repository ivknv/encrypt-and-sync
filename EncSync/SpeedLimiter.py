# -*- coding: utf-8 -*-

import time

__all__ = ["SpeedLimiter"]

class Sleeper(object):
    def __init__(self):
        self._time_wasted = 0.0

    def sleep(self, duration):
        t1 = time.time()

        if duration > self._time_wasted:
            time.sleep(duration - self._time_wasted)

        t2 = time.time()

        self._time_wasted += t2 - t1 - duration

class SpeedLimiter(object):
    def __init__(self, limit=float("inf"), interval=1.0):
        self._quantity = 0
        self.limit = limit
        self.interval = interval
        self._last_delay = time.time()
        self._sleeper = Sleeper()

    def begin(self):
        self._last_delay = time.time()

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        self._quantity = value

    def sleep(self, duration):
        self._sleeper.sleep(duration)

    def delay(self):
        dt = min(time.time() - self._last_delay, self.interval)

        sleep_duration = self._quantity / self.limit - dt

        if sleep_duration > 0.0:
            self.sleep(sleep_duration)

        self._quantity = 0
        self._last_delay = time.time()
