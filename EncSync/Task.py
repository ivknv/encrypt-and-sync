#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from collections import Counter
import traceback

from .Event import EventHandler

class Task(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.status = None
        self.parent = None
        self.progress = Counter()

        self.add_event("status_changed")

        self.lock = threading.Lock()

    def update_status(self):
        pass

    def change_status(self, new_status, lock=True):
        if self.status == new_status:
            return

        if lock:
            self.lock.acquire()
        try:
            if self.parent is not None:
                with self.parent.lock:
                    if self.status is not None:
                        self.parent.progress[self.status] -= 1

                    self.status = new_status

                    if self.status is not None:
                        self.parent.progress[self.status] += 1

                    self.parent.update_status()
            else:
                self.status = new_status

            self.emit_event("status_changed")
        finally:
            if lock:
                self.lock.release()
