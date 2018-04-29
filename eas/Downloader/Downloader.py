#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Logging import logger
from .Target import DownloadTarget
from ..Worker import Worker
from ..LogReceiver import LogReceiver

__all__ = ["Downloader"]

class Downloader(Worker):
    """
        Events: next_target, next_task, error
    """

    def __init__(self, config, directory, n_workers=2):
        Worker.__init__(self)

        self.config = config
        self.targets = []
        self.n_workers = n_workers
        self.directory = directory

        self.targets_lock = threading.Lock()
        self._upload_limit = float("inf") # Bytes per second
        self._download_limit = float("inf") # Bytes per second

        self.cur_target = None

        self.add_receiver(LogReceiver(logger))

    @property
    def upload_limit(self):
        return self._upload_limit

    @upload_limit.setter
    def upload_limit(self, value):
        self._upload_limit = value

        for target in self.get_targets() + [self.cur_target]:
            if target is None:
                continue

            target.upload_limit = value

    @property
    def download_limit(self):
        return self._download_limit

    @download_limit.setter
    def download_limit(self, value):
        self._download_limit = value

        for target in self.get_targets() + [self.cur_target]:
            if target is None:
                continue

            target.download_limit = value

    def change_status(self, status):
        for i in self.get_targets() + [self.cur_target]:
            if i is not None:
                i.status = status

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def make_target(self, src_storage_name, src_path, dst_storage_name, dst_path):
        target = DownloadTarget(self, src_storage_name, dst_storage_name)
        target.src_path = src_path
        target.dst_path = dst_path

        return target

    def add_download(self, name, src_path, dst_storage_name, dst_path):
        target = self.make_target(name, src_path, dst_storage_name, dst_path)

        self.add_target(target)

        return target

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

        return target

    def stop(self):
        Worker.stop(self)

        # Intentional assignment for thread safety
        target = self.cur_target

        if target is not None:
            target.stop()

    def work(self):
        while not self.stopped:
            try:
                with self.targets_lock:
                    try:
                        self.cur_target = self.targets.pop(0)
                    except IndexError:
                        break

                self.emit_event("next_target", self.cur_target)
                self.cur_target.complete(self)
            except Exception as e:
                self.emit_event("error", e)
                if self.cur_target is not None:
                    self.cur_target.status = "failed"
            finally:
                self.cur_target = None
