#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from ..Worker import Worker
from .Workers import LocalScanWorker, RemoteScanWorker
from .Logging import logger
from ..FileList import LocalFileList, RemoteFileList, DuplicateList
from ..Scannable import LocalScannable, RemoteScannable

class ScannerDispatcher(Worker):
    def __init__(self, scanner):
        Worker.__init__(self)

        self.scanner = scanner
        self.encsync = scanner.encsync
        self.n_workers = scanner.n_workers

        self.targets = self.scanner.targets
        self.targets_lock = self.scanner.targets_lock

        self.cur_target = None

        self.shared_llist = LocalFileList()
        self.shared_rlist = RemoteFileList()
        self.shared_duplist = DuplicateList()

        self.pool = []
        self.pool_lock = threading.Lock()

    def stop_condition(self):
        return self.stopped

    def wait_workers(self):
        logger.debug("Waiting workers")
        workers = self.get_worker_list()

        while True:
            for worker in workers:
                worker.wait_idle()

            workers = self.get_worker_list()

            if all(worker.is_idle() for worker in workers):
                logger.debug("Done waiting workers")
                return

    def get_next_target(self):
        with self.targets_lock:
            if len(self.targets):
                target = self.targets.pop(0)
                logger.debug("Next {} target: {}".format(target.type, target.path))
                return target

    def add_scannable(self, scannable):
        with self.pool_lock:
            self.pool.append(scannable)

        for w in self.get_worker_list():
            w.set_dirty()

    def get_next_scannable(self):
        with self.pool_lock:
            if len(self.pool) > 0:
                return self.pool.pop(0)

    def begin_remote_scan(self, target):
        self.shared_rlist.remove_node_children(target.path)

        scannable = RemoteScannable(self.encsync, target.path)
        scannable.identify()
        self.shared_rlist.insert_node(scannable.to_node())
        self.add_scannable(scannable)

    def begin_local_scan(self, target):
        self.shared_llist.remove_node_children(target.path)

        scannable = LocalScannable(target.path)
        scannable.identify()
        self.shared_llist.insert_node(scannable.to_node())
        self.add_scannable(scannable)

    def work(self):
        assert(self.n_workers >= 1)

        logger.debug("Dispatcher is working")

        self.shared_llist.create()
        self.shared_rlist.create()
        self.shared_duplist.create()

        while not self.stop_condition():
            target = self.get_next_target()

            if target is None:
                break

            self.cur_target = target

            assert(target.type in ("local", "remote"))

            filelist = {"local":  self.shared_llist,
                        "remote": self.shared_rlist}[target.type]

            try:
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
            except:
                target.change_status("failed")
                filelist.rollback()
                self.shared_duplist.rollback()
                logger.exception("An error occured")
            finally:
                self.cur_target = None

        logger.debug("Dispatcher is done working")
