#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from .Dispatcher import ScannerDispatcher
from ..Dispatcher import DispatcherProxy
from .Target import ScanTarget
from .Logging import logger

class Scanner(DispatcherProxy):
    def __init__(self, encsync, n_workers=2):
        DispatcherProxy.__init__(self)

        self.encsync = encsync
        self.targets = []
        self.n_workers = n_workers

        self.targets_lock = threading.Lock()

    def setup_worker(self):
        self.worker = ScannerDispatcher(self)
        logger.debug("Set up dispatcher worker")

    def start(self):
        logger.debug("Starting scanner")
        DispatcherProxy.start(self)
        logger.debug("Done starting scanner")

    def change_status(self, status):
        with self.targets_lock:
            for i in self.targets:
                i.change_status(status)

    def add_dir(self, scan_type, path):
        target = ScanTarget(scan_type, path)

        self.add_target(target)

        return target

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

    def add_local_dir(self, path):
        return self.add_dir("local", path)

    def add_remote_dir(self, path):
        return self.add_dir("remote", path)
