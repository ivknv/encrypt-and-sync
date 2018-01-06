#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from collections import Counter

from .Event.Emitter import Emitter

__all__ = ["Task"]

class Task(Emitter):
    def __init__(self):
        Emitter.__init__(self)

        self._status = None
        self._parent = None
        self._expected_total_children = 0
        self._total_children = 0
        self._progress = Counter()

        self._lock = threading.RLock()

        self.add_event("status_changed")

    def __del__(self):
        self.parent = None

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        with self._lock:
            if self._parent == value:
                return

            if self._parent is not None:
                self._parent._total_children -= 1

            self._parent = value

            if self._parent is not None:
                self._parent._total_children += 1

    @property
    def total_children(self):
        with self._lock:
            return max(self._expected_total_children, self._total_children)

    @total_children.setter
    def total_children(self, value):
        with self._lock:
            self._expected_total_children = value

    @property
    def status(self):
        with self._lock:
            return self._status

    @status.setter
    def status(self, new_status):
        with self._lock:
            old_status = self.status

            if old_status == new_status:
                return

            self._status = new_status

            if self.parent is not None:
                with self.parent._lock:
                    self.parent.progress[old_status] -= 1
                    self.parent.progress[new_status] += 1

        self.emit_event("status_changed")

    @property
    def progress(self):
        with self._lock:
            return self._progress
