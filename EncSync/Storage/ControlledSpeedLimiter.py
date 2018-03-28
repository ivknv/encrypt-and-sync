# -*- coding: utf-8 -*-

import time

from ..SpeedLimiter import SpeedLimiter

__all__ = ["ControlledSpeedLimiter"]

class ControlledSpeedLimiter(SpeedLimiter):
    def __init__(self, controller, *args, **kwargs):
        SpeedLimiter.__init__(self, *args, **kwargs)

        self.controller = controller

    def sleep(self, duration):
        tolerance = 0.001
        check_interval = 0.25
        t1 = time.time()

        left_to_sleep = duration

        while not self.controller.stopped and left_to_sleep > tolerance:
            time.sleep(min(left_to_sleep, check_interval))

            left_to_sleep = duration - (time.time() - t1)
