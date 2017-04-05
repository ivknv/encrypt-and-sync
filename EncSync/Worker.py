#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Event import Emitter

class Worker(threading.Thread, Emitter):
    def __init__(self, parent, daemon=False):
        threading.Thread.__init__(self, daemon=daemon)
        Emitter.__init__(self)

        self.stopped = False

        self.parent = parent

        # Synchronization lock
        if parent is not None:
            self.sync_lock = parent.get_sync_lock()
        else:
            self.sync_lock = threading.Lock()

        self.add_event("started")
        self.add_event("stopping")
        self.add_event("finished")

    def get_info(self):
        return {}

    def get_sync_lock(self):
        return self.sync_lock

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
        self.emit_event("started")

        try:
            self.before_work()

            try:
                self.work()
            finally:
                self.after_work()
        finally:
            self.emit_event("finished")
