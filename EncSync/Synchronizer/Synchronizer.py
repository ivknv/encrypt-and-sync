#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Target import SyncTarget
from .Logging import logger
from ..Worker import Worker
from ..LogReceiver import LogReceiver
from ..TargetStorage import get_target_storage

__all__ = ["Synchronizer"]

class Synchronizer(Worker):
    def __init__(self, encsync, directory, n_workers=2, n_scan_workers=2,
                 enable_journal=True):
        Worker.__init__(self)

        self.encsync = encsync
        self.n_workers = n_workers
        self.n_scan_workers = n_scan_workers
        self.directory = directory
        self.enable_journal = enable_journal

        self.targets = []
        self.targets_lock = threading.Lock()

        self.speed_limit = float("inf") # Bytes per second

        self.cur_target = None

        self.add_event("next_target")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def change_status(self, status):
        for i in self.get_targets() + [self.cur_target]:
            if i is not None:
                i.status = status

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

        return target

    def make_target(self, name, enable_scan, skip_integrity_check=False):
        try:
            encsync_target = self.encsync.targets[name]
        except KeyError:
            raise ValueError("Unknown target: %r" % (name,))

        src_name = encsync_target["src"]["name"]
        dst_name = encsync_target["dst"]["name"]

        src = get_target_storage(src_name)(name, "src", self.encsync, self.directory)
        dst = get_target_storage(dst_name)(name, "dst", self.encsync, self.directory)
        
        target = SyncTarget(self)
        target.name = name
        target.src = src
        target.dst = dst
        target.enable_scan = enable_scan
        target.skip_integrity_check = skip_integrity_check

        return target

    def add_new_target(self, name, enable_scan, skip_integrity_check=False):
        target = self.make_target(name, enable_scan, skip_integrity_check)

        self.add_target(target)

        return target

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def set_speed_limit(self, limit):
        self.speed_limit = limit / float(self.n_workers)

        for worker in self.get_worker_list():
            worker.speed_limit = self.speed_limit

    def work(self):
        assert(self.n_workers >= 1)

        while not self.stopped:
            with self.targets_lock:
                try:
                    target = self.targets.pop(0)
                except IndexError:
                    break

                self.cur_target = target

            try:
                self.emit_event("next_target", target)

                if target.status == "suspended":
                    self.cur_target = None
                    continue

                target.status = "pending"
                target.complete(self)

                self.cur_target = None
            except Exception as e:
                self.emit_event("error", e)
                self.cur_target.status = "failed"
