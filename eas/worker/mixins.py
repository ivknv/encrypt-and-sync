# -*- coding: utf-8 -*-

import threading

__all__ = ["SupportsDirtyMixin", "WaiterMixin", "PoolWorkerMixin", "PoolWaiterMixin"]

def _periodic_wait(event, timeout=None, interval=0.5):
    if interval is None:
        return event.wait(timeout)
    elif timeout is None:
        while not event.is_set():
            if event.wait(interval):
                return True
    else:
        interval = min(interval, timeout)

        while not event.is_set() and timeout > 0.0:
            last_time = time.monotonic()

            if event.wait(interval):
                return True

            timeout -= time.monotonic() - last_time

    return False

class SupportsDirtyMixin(object):
    def __init__(self):
        self._dirty = threading.Event()
        self._idle = threading.Event()

    def stop(self):
        super().stop()
        self.set_dirty()

    def set_dirty(self):
        self._dirty.set()
        self._idle.clear()

    def set_idle(self):
        self._dirty.clear()
        self._idle.set()

    def is_idle(self):
        return self._idle.is_set()

    def wait_idle(self, timeout=None, interval=0.5):
        return _periodic_wait(self._idle, timeout, interval)

    def wait_dirty(self, timeout=None, interval=0.5):
        return _periodic_wait(self._dirty, timeout, interval)

class WaiterMixin(object):
    def get_task(self):
        raise NotImplementedError

    def handle_task(self, task):
        raise NotImplementedError

    def set_dirty(self):
        raise NotImplementedError

    def set_idle(self):
        raise NotImplementedError

    def wait_dirty(self, timeout=None):
        raise NotImplementedError

    def work(self):
        try:
            self.set_dirty()

            while not self.stopped:
                self.wait_dirty()

                if self.stopped:
                    break

                try:
                    task = self.get_task()
                except StopIteration:
                    self.set_idle()
                    continue

                if self.stopped or self.handle_task(task) is False:
                    break
        finally:
            self.set_idle()

class PoolWorkerMixin(object):
    def work(self):
        while not self.stopped:
            try:
                task = self._pool().get_task()
            except StopIteration:
                break

            if self.stopped or self.handle_task(task) is False:
                break

class PoolWaiterMixin(object):
    def get_task(self):
        return self._pool().get_task()
