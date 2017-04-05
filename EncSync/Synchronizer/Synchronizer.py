#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import os

from .. import SyncList
from ..SyncList import pad_size
from ..Encryption import MIN_ENC_SIZE
from .. import paths
from .SyncTask import SyncTask, SyncTarget
from .Workers import UploadWorker, MkdirWorker, RmWorker
from .Workers import LocalScanWorker, RemoteScanWorker

from ..Dispatcher import StagedDispatcher

from .Logging import logger

class Synchronizer(object):
    def __init__(self, encsync, n_workers=2):
        self.encsync = encsync
        self.n_workers = n_workers
        self._dispatcher = None

        self.targets = []
        self.targets_lock = threading.Lock()

        self.speed_limit = 1024**4 / self.n_workers # Bytes per second

        self.scanned_local_dirs = set()

    def set_speed_limit(self, limit):
        self.speed_limit = int(limit / self.n_workers)
        self.dispatcher.set_speed_limit(limit)

    @property
    def dispatcher(self):
        if self._dispatcher is None:
            self._dispatcher = SynchronizerDispatcher(self)

        return self._dispatcher

    @dispatcher.setter
    def dispatcher(self, value):
        self._dispatcher = value

        return self.dispatcher

    def add_existing_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

        return target

    def add_target(self, local, remote, status="pending"):
        target = SyncTarget(self, local, remote)

        target.change_status(status)

        self.add_existing_target(target)

        return target

    def stop(self):
        self.dispatcher.stop()

    def get_worker_list(self):
        return self.dispatcher.get_worker_list()

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def start(self):
        self.dispatcher.start()

    def start_if_not_alive(self):
        if not self.is_alive():
            self.start()

    def is_alive(self):
        return self.dispatcher.is_alive()

    def join(self):
        self.dispatcher.join_workers()
        self.dispatcher.join()

class SynchronizerDispatcher(StagedDispatcher):
    def __init__(self, synchronizer):
        StagedDispatcher.__init__(self)

        self.synchronizer = synchronizer

        self.n_workers = synchronizer.n_workers
        self.encsync = synchronizer.encsync

        self.targets = synchronizer.targets
        self.targets_lock = synchronizer.targets_lock

        self.cur_target = None
        self.diffs = None

        self.shared_synclist = SyncList.SyncList()

        self.scanned_local_dirs = synchronizer.scanned_local_dirs
        self.speed_limit = synchronizer.speed_limit

        self.stage_order = ("scan", "rm", "dirs", "files", "check")

        self.add_stage("scan",  self.init_scan_stage,  self.finalize_scan_stage)
        self.add_stage("rm",    self.init_rm_stage,    self.finalize_rm_stage)
        self.add_stage("dirs",  self.init_dirs_stage,  self.finalize_dirs_stage)
        self.add_stage("files", self.init_files_stage, self.finalize_files_stage)
        self.add_stage("check", self.init_check_stage, self.finalize_check_stage)

    def set_speed_limit(self, limit):
        self.speed_limit = int(limit / self.n_workers)

        for worker in self.get_worker_list():
            worker.speed_limit = self.speed_limit

    def get_next_task(self):
        if not self.available:
            return

        with self.get_sync_lock():
            if not self.available:
                logger.debug("Dispatcher is not available")
                return

            try:
                diff = next(self.diffs)
            except StopIteration:
                logger.debug("Dispatcher.get_next_task(): no more diffs")
                return

            task = SyncTask()
            task.parent = self.cur_target

            if diff[0] == "new" and diff[1] == "f":
                size = os.path.getsize(paths.to_sys(diff[2].local))
                task.size = pad_size(size) + MIN_ENC_SIZE

            task.diff = diff

            task.path = diff[2]

            task.change_status("pending")

            return task

    def build_diffs_table(self):
        assert(self.cur_target is not None)

        difflist = SyncList.DiffList(self.encsync)

        with difflist:
            diffs = SyncList.compare_lists(self.encsync,
                                           self.cur_target.local,
                                           self.cur_target.remote)

            try:
                difflist.begin_transaction()
                difflist.clear_differences(self.cur_target.local,
                                           self.cur_target.remote)
                difflist.insert_differences(diffs)
                difflist.commit()
            except Exception as e:
                difflist.rollback()
                raise e

        if self.stage != "check":
            diff_count = difflist.get_difference_count(self.cur_target.local,
                                                       self.cur_target.remote)
            n_done = self.cur_target.get_n_done()

            self.cur_target.total_children = diff_count + n_done

    def work(self):
        try:
            logger.debug("Dispatcher started working")

            synclist = SyncList.SyncList()
            synclist.create()

            difflist = SyncList.DiffList(self.encsync)
            difflist.create()

            while not self.stopped:
                with self.targets_lock:
                    if self.stopped or not len(self.targets):
                        break

                    target = self.targets.pop(0)
                    self.cur_target = target

                logger.debug("Dispatcher is working on a new task")

                if target.status == "suspended":
                    self.cur_target = None
                    continue

                assert(self.stage is None)

                self.available = True

                stages = self.stage_order

                if target.stage is not None:
                    # Skip completed stages
                    idx = self.stage_order.index(target.stage)
                    stages = self.stage_order[idx:]

                if target.stage not in {None, "scan", "check"}:
                    self.build_diffs_table()

                for stage in stages:
                    if self.stopped:
                        break

                    target.stage = stage

                    self.run_stage(stage)

                    self.reset_diffs()

                    if target.status == "suspended":
                        break

                if target.total_children == 0:
                    target.change_status("finished")

                if target.status == "finished":
                    target.stage = None
                    difflist.clear_differences(target.local, target.remote)

                self.cur_target = None
            logger.debug("Dispatcher finished working")

            assert(self.stage is None)
        finally:
            self.synchronizer.dispatcher = None

    def init_rm_stage(self):
        logger.debug("Dispatcher began initializing stage 'rm'")

        d = SyncList.DiffList(self.encsync)
        self.diffs = d.select_rm_differences(self.cur_target.local,
                                             self.cur_target.remote)

        self.shared_synclist.begin_transaction()

        self.start_workers(self.n_workers, RmWorker, self)

        logger.debug("Dispatcher finished initializing stage 'rm'")

    def finalize_rm_stage(self):
        self.shared_synclist.commit()

    def init_dirs_stage(self):
        logger.debug("Dispatcher began initializing stage 'dirs'")

        d = SyncList.DiffList(self.encsync)
        self.diffs = d.select_dirs_differences(self.cur_target.local,
                                               self.cur_target.remote)

        self.shared_synclist.begin_transaction()

        self.start_worker(MkdirWorker, self)

        logger.debug("Dispatcher finished initializing stage 'dirs'")

    def finalize_dirs_stage(self):
        self.shared_synclist.commit()

    def init_files_stage(self):
        logger.debug("Dispatcher began initializing stage 'files'")

        d = SyncList.DiffList(self.encsync)
        self.diffs = d.select_files_differences(self.cur_target.local,
                                                self.cur_target.remote)

        self.shared_synclist.begin_transaction()

        self.start_workers(self.n_workers, UploadWorker, self)

        logger.debug("Dispatcher finished initializing stage 'files'")

    def finalize_files_stage(self):
        self.shared_synclist.commit()

    def init_scan_stage(self):
        try:
            self.start_worker(LocalScanWorker, self).join()
            self.start_worker(RemoteScanWorker, self)
        except:
            logger.exception("An error occured")
            self.cur_target.change_status("failed")

    def finalize_scan_stage(self):
        try:
            if self.cur_target.status != "pending" or self.stopped:
                return

            self.build_diffs_table()

            self.cur_target.emit_event("scan_finished")
        except:
            logger.exception("An error occured")
            self.cur_target.change_status("failed")

    def init_check_stage(self):
        try:
            if self.cur_target.skip_integrity_check:
                return

            self.cur_target.change_status("pending")

            self.start_worker(RemoteScanWorker, self, force=True)
        except:
            self.cur_target.change_status("failed")
            logger.exception("An error occured")

    def finalize_check_stage(self):
        try:
            if self.cur_target.status != "pending" or self.stopped:
                return

            if self.cur_target.skip_integrity_check:
                return

            diffs = SyncList.compare_lists(self.encsync,
                                           self.cur_target.local, self.cur_target.remote)


            self.build_diffs_table()

            self.cur_target.emit_event("integrity_check_finished")

            difflist = SyncList.DiffList(self.encsync)

            if difflist.get_difference_count(self.cur_target.local, self.cur_target.remote):
                self.cur_target.change_status("failed")
                self.cur_target.emit_event("integrity_check_failed")
            else:
                self.cur_target.change_status("finished")
        except:
            self.cur_target.change_status("failed")
            logger.exception("An error occured")

    def reset_diffs(self):
        self.diffs = None
