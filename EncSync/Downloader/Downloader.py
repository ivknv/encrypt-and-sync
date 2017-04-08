#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import os

from .. import paths

from .Dispatcher import DownloaderDispatcher

from .Logging import logger

class Downloader(object):
    def __init__(self, encsync, n_workers=2):
        self.encsync = encsync
        self.targets = []
        self.n_workers = n_workers
        self.dispatcher = None
        self.targets_lock = threading.Lock()
        self.speed_limit = 1024**4 / n_workers # Bytes per second

    def change_status(self, status):
        for i in self.get_targets():
            i.change_status("suspended")

    def get_worker_list(self):
        if self.dispatcher is not None:
            return self.dispatcher.get_worker_list()
        else:
            return []

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

    def start_dispatcher(self):
        logger.debug("Starting dispatcher")
        self.dispatcher = DownloaderDispatcher(self)
        self.dispatcher.start()
        logger.debug("Done starting dispatcher")

    def start(self):
        self.start_dispatcher()

    def start_if_not_alive(self):
        if not self.is_alive():
            self.start()

    def stop(self):
        if self.dispatcher is not None:
            self.dispatcher.stop()

    def is_alive(self):
        return self.dispatcher is not None and self.dispatcher.is_alive()

    def join(self):
        if self.dispatcher is not None:
            self.dispatcher.join()

    def full_stop(self):
        self.dispatcher.full_stop()
