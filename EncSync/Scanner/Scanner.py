#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Logging import logger
from .Target import ScanTarget
from ..Worker import Worker
from ..LogReceiver import LogReceiver

class Scanner(Worker):
    def __init__(self, encsync, directory, n_workers=2, enable_journal=True):
        Worker.__init__(self)

        self.encsync = encsync
        self.n_workers = n_workers
        self.directory = directory
        self.enable_journal = enable_journal

        self.targets = []
        self.targets_lock = threading.Lock()

        self.cur_target = None

        self.tasks = []
        self.tasks_lock = threading.Lock()

        self.add_event("next_target")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def change_status(self, status):
        with self.targets_lock:
            for i in self.targets + [self.cur_target]:
                if i is not None:
                    i.status = status

    def add_new_target(self, scan_type, name):
        target = self.make_target(scan_type, name)
        self.add_target(target)

        return target

    def make_target(self, scan_type, name):
        if scan_type not in ("src", "dst"):
            msg = "Unknown scan_type: %r, must be 'src' or 'dst'" % (scan_type,)
            raise ValueError(msg)

        try:
            encsync_target = self.encsync.targets[name]
        except KeyError:
            raise ValueError("Unknown target: %r" % (name,))

        target_dir = encsync_target[scan_type]

        path = target_dir["path"]
        encrypted = target_dir["encrypted"]
        filename_encoding = target_dir["filename_encoding"]
        storage = self.encsync.storages[target_dir["name"]]

        target = ScanTarget(self, name, storage)
        target.type = scan_type
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

    def add_task(self, task):
        with self.tasks_lock:
            self.tasks.append(task)

        for w in self.get_worker_list():
            w.set_dirty()

    def get_next_task(self):
        with self.tasks_lock:
            try:
                return self.tasks.pop(0)
            except IndexError:
                pass

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
