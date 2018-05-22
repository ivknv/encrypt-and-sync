# -*- coding: utf-8 -*-

import threading

__all__ = ["SupportsDirtyMixin", "WaiterMixin", "PoolWorkerMixin", "PoolWaiterMixin"]

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

    def wait_idle(self, timeout=None):
        self._idle.wait(timeout)

    def wait_dirty(self, timeout=None):
        self._dirty.wait(timeout)

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
