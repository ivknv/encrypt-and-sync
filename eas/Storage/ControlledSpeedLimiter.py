# -*- coding: utf-8 -*-

import time
import weakref

from ..common import SpeedLimiter

__all__ = ["ControlledSpeedLimiter"]

class ControlledSpeedLimiter(SpeedLimiter):
    def __init__(self, controller, *args, **kwargs):
        SpeedLimiter.__init__(self, *args, **kwargs)

        self.weak_controller = weakref.finalize(controller, lambda: None)

    def sleep(self, duration):
        controller = self.weak_controller.peek()[0]

        tolerance = 0.001
        check_interval = 0.25
        t1 = time.time()

        left_to_sleep = duration

        while not controller.stopped and left_to_sleep > tolerance:
            time.sleep(min(left_to_sleep, check_interval))

            left_to_sleep = duration - (time.time() - t1)
