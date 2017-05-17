#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import os

from .. import Paths

from .Dispatcher import DownloaderDispatcher
from ..Dispatcher import DispatcherProxy
from .DownloadTarget import DownloadTarget

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
            i.change_status(status)

    def set_speed_limit(self, limit):
        self.speed_limit = limit / self.n_workers
        if self.dispatcher is not None:
            self.dispatcher.set_speed_limit(self.speed_limit)

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def add_download(self, remote_prefix, remote, local):
        target = DownloadTarget()
        target.local = Paths.to_sys(local)
        target.dec_remote = remote
        target.prefix = remote_prefix

        self.add_target(target)

        return target

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

        return target

    def setup_worker(self):
        self.worker = DownloaderDispatcher(self)
