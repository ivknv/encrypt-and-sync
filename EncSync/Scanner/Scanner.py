#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Logging import logger
from .Target import ScanTarget
from ..Worker import Worker
from ..LogReceiver import LogReceiver

class Scanner(Worker):
    def __init__(self, config, directory, n_workers=2, enable_journal=True):
        Worker.__init__(self)

        self.config = config
        self.n_workers = n_workers
        self.directory = directory
        self.enable_journal = enable_journal

        self.targets = []
        self.targets_lock = threading.Lock()

        self.cur_target = None

        self.add_event("next_target")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def change_status(self, status):
        with self.targets_lock:
            for i in self.targets + [self.cur_target]:
                if i is not None:
                    i.status = status

    def add_new_target(self, folder_name):
        target = self.make_target(folder_name)
        self.add_target(target)

        return target

    def make_target(self, folder_name):
        try:
            folder = self.config.folders[folder_name]
        except KeyError:
            raise ValueError("Unknown folder: %r" % (folder_name,))

        path = folder["path"]
        encrypted = folder["encrypted"]
        filename_encoding = folder["filename_encoding"]
        storage = self.config.storages[folder["type"]]

        target = ScanTarget(self, folder_name, storage)
        target.type = folder["type"]
        target.encrypted = encrypted
        target.path = path
        target.filename_encoding = filename_encoding

        return target

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def stop_condition(self):
        return self.stopped

    def stop(self):
        Worker.stop(self)

        # Intentional assignment for thread safety
        target = self.cur_target

        if target is not None:
            target.stop()

    def wait_workers(self):
        workers = self.get_worker_list()

        while True:
            for worker in workers:
                worker.wait_idle()

            workers = self.get_worker_list()

            if all(worker.is_idle() for worker in workers):
                return

    def get_next_target(self):
        with self.targets_lock:
            if len(self.targets):
                target = self.targets.pop(0)
                self.emit_event("next_target", target)
                return target

    def work(self):
        assert(self.n_workers >= 1)

        target = None

        while not self.stop_condition():
            try:
                target = self.get_next_target()

                if target is None:
                    break

                self.cur_target = target

                if target.status == "suspended":
                    continue

                target.complete(self)
            except Exception as e:
                try:
                    self.emit_event("error", e)
                    if target is not None:
                        target.status = "failed"
                finally:
                    self.cur_target = None
