# -*- coding: utf-8 -*-

import time

from ..common import SpeedLimiter

__all__ = ["StoppableSpeedLimiter"]

class StoppableSpeedLimiter(SpeedLimiter):
    def __init__(self, *args, **kwargs):
        SpeedLimiter.__init__(self, *args, **kwargs)

        self.stopped = False

    def stop(self):
        self.stopped = True

    def sleep(self, duration):
        tolerance = 0.001
        check_interval = 0.25
        t1 = time.monotonic()

        left_to_sleep = duration

        while not self.stopped and left_to_sleep > tolerance:
            super().sleep(min(left_to_sleep, check_interval))

            left_to_sleep = duration - (time.monotonic() - t1)
