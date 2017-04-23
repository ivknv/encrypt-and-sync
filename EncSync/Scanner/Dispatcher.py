#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from ..Dispatcher import Dispatcher
from .Workers import LocalScanWorker, RemoteScanWorker
from .Logging import logger
from .. import SyncList
from ..Scannable import LocalScannable, RemoteScannable

class ScannerDispatcher(Dispatcher):
    def __init__(self, scanner):
        Dispatcher.__init__(self)

        self.scanner = scanner
        self.encsync = scanner.encsync
        self.n_workers = scanner.n_workers

        self.targets = self.scanner.targets
        self.targets_lock = self.scanner.targets_lock

        self.cur_target = None

        self.shared_synclist = SyncList.SyncList()

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
        self.shared_synclist.remove_remote_node_children(target.path)

        scannable = RemoteScannable(self.encsync, target.path)
        self.add_scannable(scannable)

    def begin_local_scan(self, target):
        self.shared_synclist.remove_local_node_children(target.path)

        scannable = LocalScannable(target.path)
        self.add_scannable(scannable)

    def work(self):
        assert(self.n_workers >= 1)

        logger.debug("Dispatcher is working")

        self.shared_synclist.create()

        while not self.stop_condition():
            target = self.get_next_target()

            if target is None:
                break

            self.cur_target = target

            assert(target.type in ("local", "remote"))

            try:
                if target.status == "suspended":
                    continue

                target.change_status("pending")

                self.shared_synclist.begin_transaction()

                if target.type == "local":
                    self.start_worker(LocalScanWorker, self, target)
                    self.begin_local_scan(target)
                elif target.type == "remote":
                    self.start_workers(self.n_workers, RemoteScanWorker, self, target)
                    self.begin_remote_scan(target)

                    self.wait_workers()
                    self.stop_workers()

                logger.debug("Joining workers")
                self.join_workers()
                logger.debug("Done joining workers")

                if target.status == "pending":
                    self.shared_synclist.commit()
                    target.change_status("finished")
                else:
                    self.shared_synclist.rollback()
            except:
                target.change_status("failed")
                self.shared_synclist.rollback()
                logger.exception("An error occured")
            finally:
                self.cur_target = None

        logger.debug("Dispatcher is done working")
