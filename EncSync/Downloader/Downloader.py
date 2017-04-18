#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import os

from .. import paths

from .Dispatcher import DownloaderDispatcher
from ..Dispatcher import DispatcherProxy

from .Logging import logger

class Downloader(DispatcherProxy):
    def __init__(self, encsync, n_workers=2):
        DispatcherProxy.__init__(self)

        self.encsync = encsync
        self.targets = []
        self.n_workers = n_workers
        self.targets_lock = threading.Lock()
        self.speed_limit = 1024**4 / n_workers # Bytes per second

    @property
    def dispatcher(self):
        return self.worker

    @dispatcher.setter
    def dispatcher(self, value):
        self.worker = value

    def change_status(self, status):
        for i in self.get_targets():
            i.change_status("suspended")

    def set_speed_limit(self, limit):
        self.speed_limit = limit / self.n_workers
        if self.dispatcher is not None:
            self.dispatcher.set_speed_limit(self.speed_limit)

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def add_target(self, target):
        target.local = paths.to_sys(target.local)
        if target.dec_remote is None:
            target.dec_remote, target.IVs = self.encsync.decrypt_path(target.remote, target.prefix)

        if target.status is None:
            target.change_status("pending")
        if target.type == "file" and os.path.isdir(target.local):
            name = paths.split(target.dec_remote)[1]
            target.local = os.path.join(target.local, name)

        with self.targets_lock:
            self.targets.append(target)

    def setup_worker(self):
        self.worker = DownloaderDispatcher(self)
