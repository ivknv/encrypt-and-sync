#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .SyncTask import SyncTarget

from ..Dispatcher import DispatcherProxy
from .Dispatcher import SynchronizerDispatcher

class Synchronizer(DispatcherProxy):
    def __init__(self, encsync, n_workers=2, n_scan_workers=2):
        DispatcherProxy.__init__(self)

        self.encsync = encsync
        self.n_workers = n_workers
        self.n_scan_workers = n_scan_workers

        self.targets = []
        self.targets_lock = threading.Lock()

        self.speed_limit = 1024**4 / self.n_workers # Bytes per second

    @property
    def dispatcher(self):
        return self.worker

    @dispatcher.setter
    def dispatcher(self, value):
        self.worker = value

    def change_status(self, status):
        for i in self.get_targets():
            i.change_status(status)

    def set_speed_limit(self, limit):
        self.speed_limit = int(limit / self.n_workers)
        self.worker.set_speed_limit(limit)

    def setup_worker(self):
        self.worker = SynchronizerDispatcher(self)

    def add_existing_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

        return target

    def add_target(self, enable_scan, local, remote, status="pending"):
        target = SyncTarget(self, local, remote)
        target.enable_scan = enable_scan

        target.change_status(status)

        self.add_existing_target(target)

        return target

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)
