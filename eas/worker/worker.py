# -*- coding: utf-8 -*-

import sys
import time

from ..events import Emitter

__all__ = ["Worker"]

if sys.platform.startswith("win"):
    DEFAULT_JOIN_INTERVAL = 1
else:
    DEFAULT_JOIN_INTERVAL = None

class Worker(Emitter):
    """
        Events: started, stopping, finished
    """

    def __init__(self):
        Emitter.__init__(self)

        self.stopped = False

        self.retval = None

    def get_info(self):
        return {}

    def stop(self):
        self.stopped = True
        self.emit_event("stopping")

    def before_work(self):
        pass

    def work(self):
        pass

    def after_work(self):
        pass

    def run(self):
        self.stopped = False
        self.emit_event("started")

        try:
            self.before_work()

            try:
                self.retval = self.work()
            finally:
                self.after_work()
        finally:
            self.emit_event("finished")

    def start(self):
        raise NotImplementedError

    def actual_join(self, timeout=None):
        raise NotImplementedError

    def join(self, timeout=None, interval=None):
        if interval is None:
            interval = DEFAULT_JOIN_INTERVAL

        if interval is None:
            self.actual_join(timeout)
        elif timeout is None:
            while self.is_alive():
                self.actual_join(interval)
        else:
            interval = min(interval, timeout)

            while self.is_alive() and timeout > 0.0:
                last_time = time.monotonic()
                self.actual_join(interval)
                timeout -= time.monotonic() - last_time

    def is_alive(self):
        raise NotImplementedError

    def start_if_not_alive(self):
        if not self.is_alive():
            self.start()
