#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import sys

from .worker_base import WorkerBase

DEFAULT_DAEMON = sys.platform.startswith("win")

class Worker(WorkerBase):
    def __init__(self, parent=None, daemon=None):
        WorkerBase.__init__(self, parent)

        if daemon is None:
            daemon = DEFAULT_DAEMON

        self.workers = {}
        self.workers_lock = threading.Lock()

        self.daemon = daemon

        self.thread = None

    def start(self):
        if self.thread is None or not self.thread.is_alive() and self.thread.ident is not None:
            self.thread = threading.Thread(target=self.run, daemon=self.daemon)
        self.thread.start()

    def actual_join(self, timeout=None):
        if self.thread is not None:
            self.thread.join(timeout)

    def is_alive(self):
        return self.thread is not None and self.thread.is_alive()

    @property
    def ident(self):
        if self.thread is None:
            return None
        return self.thread.ident

    def add_worker(self, worker):
        with self.workers_lock:
            self.workers[worker.ident] = worker

        return worker

    def join_worker(self, worker, timeout=None, interval=None):
        worker.join(timeout, interval)

        if not worker.is_alive():
            with self.workers_lock:
                self.workers.pop(worker.ident, None)

    def get_worker_list(self):
        with self.workers_lock:
            return list(self.workers.values())

    def run(self):
        WorkerBase.run(self)
