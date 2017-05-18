#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Event import EventHandler

class WorkerBase(EventHandler):
    def __init__(self, parent):
        EventHandler.__init__(self)

        self.parent = parent
        self.stopped = False

        # Synchronization lock
        if parent is not None:
            self.sync_lock = parent.get_sync_lock()
        else:
            self.sync_lock = threading.Lock()

        self.add_event("started")
        self.add_event("stopping")
        self.add_event("finished")

        self.retval = None

    def get_siblings(self):
        if self.parent is None:
            return []

        return [i for i in self.parent.get_workers() if i is not self]

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
                self.retval = self.work()
            finally:
                self.after_work()
        finally:
            self.emit_event("finished")

    def start(self):
        raise NotImplementedError

    def join(self):
        raise NotImplementedError

    def is_alive(self):
        raise NotImplementedError

    def start_if_not_alive(self):
        if not self.is_alive():
            self.start()

class WorkerProxy(WorkerBase):
    def __init__(self, parent):
        WorkerBase.__init__(self, parent)
        self._worker = None

    def setup_worker(self):
        raise NotImplementedError

    @property
    def worker(self):
        if self._worker is None:
            self.setup_worker()

        return self._worker

    @worker.setter
    def worker(self, value):
        self._worker = value

    def start(self):
        if not self.is_alive():
            self.setup_worker()

        self.worker.start()

    def join(self):
        if self.is_alive():
            self.worker.join()

    def is_alive(self):
        return self.worker.is_alive()

class Worker(threading.Thread, WorkerBase):
    def __init__(self, parent, daemon=False):
        threading.Thread.__init__(self, daemon=daemon)
        WorkerBase.__init__(self, parent)

    def run(self):
        WorkerBase.run(self)
