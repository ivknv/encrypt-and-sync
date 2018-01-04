#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Workers import *
from .Logging import logger
from .Task import ScanTask
from .Target import ScanTarget
from ..Worker import Worker
from ..FileList import FileList, DuplicateList
from ..Scannable import DecryptedScannable, EncryptedScannable
from ..LogReceiver import LogReceiver
from .. import PathMatch
from .. import Paths

class Scanner(Worker):
    def __init__(self, encsync, directory, n_workers=2, enable_journal=True):
        Worker.__init__(self)

        self.encsync = encsync
        self.n_workers = n_workers
        self.directory = directory
        self.enable_journal = enable_journal

        self.targets = []
        self.targets_lock = threading.Lock()

        self.shared_flist = None
        self.shared_duplist = None

        if not self.enable_journal:
            self.shared_duplist.disable_journal()

        self.cur_target = None

        self.pool = []
        self.pool_lock = threading.Lock()

        self.add_event("next_target")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def change_status(self, status):
        with self.targets_lock:
            for i in self.targets + [self.cur_target]:
                if i is not None:
                    i.change_status(status)

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

        target = ScanTarget(scan_type, encrypted, storage, name, path, filename_encoding)

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

    def add_task(self, scannable):
        task = ScanTask(scannable)
        with self.pool_lock:
            self.pool.append(task)

        for w in self.get_worker_list():
            w.set_dirty()

    def get_next_task(self):
        with self.pool_lock:
            if len(self.pool) > 0:
                return self.pool.pop(0)

    def begin_scan(self, target):
        self.shared_flist.clear()

        if target.encrypted:
            self.shared_duplist.remove_children(target.path)

        if self.stop_condition():
            return

        if target.encrypted:
            scannable = EncryptedScannable(target.storage, target.path,
                                           filename_encoding=target.filename_encoding)
        else:
            scannable = DecryptedScannable(target.storage, target.path)

        try:
            scannable.identify()
        except FileNotFoundError:
            return

        if self.stop_condition():
            return

        if target.storage.name == "local":
            path = Paths.from_sys(target.path)

            if scannable.type == "d":
                path = Paths.dir_normalize(path)

            if not PathMatch.match(path, self.encsync.allowed_paths):
                return

        if scannable.type is not None:
            self.shared_flist.insert_node(scannable.to_node())
            self.add_task(scannable)

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

                storage_name = target.storage.name

                self.shared_flist = FileList(target.name, storage_name, self.directory)
                self.shared_duplist = DuplicateList(storage_name, self.directory)

                if not self.enable_journal:
                    self.shared_flist.disable_journal()
                    self.shared_duplist.disable_journal()

                self.shared_flist.create()
                self.shared_duplist.create()
            except BaseException as e:
                try:
                    self.emit_event("error", e)
                    if target is not None:
                        target.change_status("failed")
                finally:
                    self.cur_target = None

                continue

            try:
                if self.stop_condition():
                    break

                target.change_status("pending")

                self.shared_flist.begin_transaction()
                self.shared_duplist.begin_transaction()

                self.begin_scan(target)

                if self.stop_condition():
                    self.shared_flist.rollback()
                    self.shared_duplist.rollback()
                    break

                if target.storage.parallelizable:
                    if target.encrypted:
                        worker_class = AsyncEncryptedScanWorker
                    else:
                        worker_class = AsyncDecryptedScanWorker

                    self.start_workers(self.n_workers, worker_class, self, target)
                    self.wait_workers()
                    self.stop_workers()
                else:
                    if target.encrypted:
                        worker_class = EncryptedScanWorker
                    else:
                        worker_class = DecryptedScanWorker

                    if self.pool:
                        self.start_worker(worker_class, self, target)

                if self.stop_condition():
                    self.stop_workers()
                    self.join_workers()
                    self.shared_flist.rollback()
                    self.shared_duplist.rollback()
                    break

                self.join_workers()

                if target.status == "pending":
                    self.shared_flist.commit()
                    self.shared_duplist.commit()
                    target.change_status("finished")

                    target.emit_event("scan_finished")
                else:
                    self.shared_flist.rollback()
                    self.shared_duplist.rollback()
            except BaseException as e:
                self.stop_workers()
                self.shared_flist.rollback()
                self.shared_duplist.rollback()

                self.emit_event("error", e)

                if target is not None:
                    target.change_status("failed")
            finally:
                self.cur_target = None
