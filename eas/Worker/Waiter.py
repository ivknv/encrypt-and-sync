#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from .Worker import Worker

__all__ = ["Waiter"]

class Waiter(Worker):
    def __init__(self, parent, daemon=None):
        Worker.__init__(self, parent, daemon)
        self._dirty = threading.Event()
        self._idle = threading.Event()

    def set_dirty(self):
        self._dirty.set()
        self._idle.clear()

    def set_idle(self):
        self._dirty.clear()
        self._idle.set()

    def is_idle(self):
        return self._idle.is_set()

    def wait_idle(self):
        self._idle.wait()

    def wait_dirty(self):
        self._dirty.wait()

    def stop(self):
        Worker.stop(self)
        self.set_dirty()

    def get_next_task(self):
        raise NotImplementedError

    def add_task(self, task):
        raise NotImplementedError

    def handle_task(self, task):
        pass

    def work(self):
        self.set_dirty()

        try:
            while not self.stopped:
                self.wait_dirty()

                if self.stopped:
                    break

                task = self.get_next_task()

                if task is None:
                    self.set_idle()
                    continue

                if not self.handle_task(task):
                    break
        finally:
            self.set_idle()
