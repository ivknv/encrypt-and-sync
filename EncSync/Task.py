#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from collections import Counter
import traceback

from .Event.EventHandler import EventHandler

class Task(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.status = None
        self.parent = None
        self.progress = Counter()

        self.add_event("status_changed")

        self.lock = threading.RLock()

    def update_status(self):
        pass

    def change_status(self, new_status):
        if self.status == new_status:
            return

        with self.lock:
            old_status = self.status
            self.status = new_status

        if self.parent is not None:
            with self.parent.lock:
                self.parent.progress[old_status] -= 1
                self.parent.progress[new_status] += 1

            self.emit_event("status_changed")

            with self.parent.lock:
                self.parent.update_status()
        else:
            self.emit_event("status_changed")
