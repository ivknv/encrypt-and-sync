#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from ..Worker import Worker
from .Workers import LocalScanWorker, RemoteScanWorker
from .Logging import logger
from ..FileList import LocalFileList, RemoteFileList, DuplicateList
from ..Scannable import LocalScannable, RemoteScannable
from .Task import ScanTask
from .Target import ScanTarget
from ..YandexDiskApi.Exceptions import DiskNotFoundError
from .. import PathMatch

class Scanner(Worker):
    def __init__(self, encsync, directory, n_workers=2):
        Worker.__init__(self)

        self.encsync = encsync
        self.n_workers = n_workers
        self.directory = directory

        self.targets = []
        self.targets_lock = threading.Lock()

        self.cur_target = None

        self.shared_llist = LocalFileList(directory)
        self.shared_rlist = RemoteFileList(directory)
        self.shared_duplist = DuplicateList(directory)

        self.pool = []
        self.pool_lock = threading.Lock()

        self.add_event("next_target")
        self.add_event("error")

    def change_status(self, status):
        with self.targets_lock:
            for i in self.targets + [self.cur_target]:
                if i is not None:
                    i.change_status(status)

    def add_dir(self, scan_type, path):
        target = ScanTarget(scan_type, path)

        self.add_target(target)

        return target

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def add_local_dir(self, path):
        return self.add_dir("local", path)

    def add_remote_dir(self, path):
        return self.add_dir("remote", path)

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

    def begin_remote_scan(self, target):
        self.shared_rlist.remove_node_children(target.path)

        scannable = RemoteScannable(self.encsync, target.path)

        try:
            scannable.identify()
        except DiskNotFoundError:
            return

        self.shared_rlist.insert_node(scannable.to_node())
        self.add_task(scannable)

    def begin_local_scan(self, target):
        self.shared_llist.remove_node_children(target.path)

        if not PathMatch.match(Paths.from_sys(target.path), self.encsync.allowed_paths):
            return

        scannable = LocalScannable(target.path)
        scannable.identify()
        self.shared_llist.insert_node(scannable.to_node())
        self.add_task(scannable)

    def work(self):
        try:
            assert(self.n_workers >= 1)

            self.shared_llist.create()
            self.shared_rlist.create()
            self.shared_duplist.create()
        except Exception as e:
            self.emit_event("error", e)
            return

        while not self.stop_condition():
            try:
                target = self.get_next_target()

                if target is None:
                    break

                self.cur_target = target

                assert(target.type in ("local", "remote"))

                filelist = {"local":  self.shared_llist,
                            "remote": self.shared_rlist}[target.type]

                if target.status == "suspended":
                    continue

                target.change_status("pending")

                filelist.begin_transaction()
                self.shared_duplist.begin_transaction()

                if target.type == "local":
                    self.start_worker(LocalScanWorker, self, target)
                    self.begin_local_scan(target)
                elif target.type == "remote":
                    self.shared_duplist.remove_children(target.path)

                    self.start_workers(self.n_workers, RemoteScanWorker, self, target)
                    self.begin_remote_scan(target)

                    self.wait_workers()
                    self.stop_workers()

                self.join_workers()

                if target.status == "pending":
                    filelist.commit()
                    self.shared_duplist.commit()
                    target.change_status("finished")

                    target.emit_event("scan_finished")
                else:
                    filelist.rollback()
                    self.shared_duplist.rollback()
            except Exception as e:
                self.stop_workers()
                filelist.rollback()
                self.shared_duplist.rollback()

                self.emit_event("error", e)

                if target is not None:
                    target.change_status("failed")
            finally:
                self.cur_target = None
