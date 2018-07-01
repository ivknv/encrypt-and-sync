# -*- coding: utf-8 -*-

from collections import Counter
import threading

from .events import Emitter

__all__ = ["Task"]

class Task(Emitter):
    """
        Events: status_changed, stop
    """

    def __init__(self):
        Emitter.__init__(self)

        self._status = None
        self._parent = None
        self.expected_total_children = 0
        self._total_children = 0
        self._progress = Counter()
        self._completed = threading.Event()
        self.stopped = False

        self._lock = threading.RLock()

    def wait(self, timeout=None):
        self._completed.wait(timeout)

    def stop(self):
        self.stopped = True
        self.emit_event("stop")

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        with self._lock:
            if self._parent == value:
                return

            if self._parent is not None:
                with self._parent._lock:
                    self._parent._total_children -= 1

            self._parent = value

            if value is not None:
                with value._lock:
                    value._total_children += 1

    @property
    def total_children(self):
        with self._lock:
            return max(self.expected_total_children, self._total_children)

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

    def complete(self):
        raise NotImplementedError

    def run(self):
        try:
            self._completed.clear()

            return self.complete()
        finally:
            self._completed.set()
