#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import os

from yadisk.exceptions import DiskNotFoundError

from .Workers import UploadWorker, MkdirWorker, RmWorker, RmDupWorker
from .SyncTask import SyncTask, SyncTarget
from .Logging import logger
from .Exceptions import LocalPathNotFoundError
from ..Scanner.Workers import LocalScanWorker, RemoteScanWorker
from ..Scanner.Task import ScanTask
from ..Scanner.Target import ScanTarget
from ..Worker import StagedWorker
from ..LogReceiver import LogReceiver
from ..FileList import LocalFileList, RemoteFileList, DuplicateList
from ..DiffList import DiffList
from ..Scannable import LocalScannable, RemoteScannable
from ..Encryption import pad_size, MIN_ENC_SIZE
from .. import PathMatch
from .. import Paths
from .. import FileComparator

class Synchronizer(StagedWorker):
    def __init__(self, encsync, directory, n_workers=2, n_scan_workers=2, enable_journal=True):
        StagedWorker.__init__(self)

        self.encsync = encsync
        self.n_workers = n_workers
        self.n_scan_workers = n_scan_workers
        self.directory = directory
        self.enable_journal = enable_journal

        self.targets = []
        self.targets_lock = threading.Lock()

        self.speed_limit = float("inf") # Bytes per second

        self.task_lock = threading.Lock()

        self.cur_target = None
        self.diffs = None

        self.shared_llist = None
        self.shared_rlist = None
        self.shared_duplist = DuplicateList(directory)
        self.difflist = DiffList(self.encsync, self.directory)

        if not self.enable_journal:
            self.shared_duplist.disable_journal()
            self.difflist.disable_journal()

        self.stage_order = ("scan", "duplicates", "rm", "dirs", "files", "check")

        self.scannables = []
        self.scannables_lock = threading.Lock()

        self.add_stage("scan",       self.init_scan_stage,       self.finalize_scan_stage)
        self.add_stage("duplicates", self.init_duplicates_stage, self.finalize_duplicates_stage)
        self.add_stage("rm",         self.init_rm_stage,         self.finalize_rm_stage)
        self.add_stage("dirs",       self.init_dirs_stage,       self.finalize_dirs_stage)
        self.add_stage("files",      self.init_files_stage,      self.finalize_files_stage)
        self.add_stage("check",      self.init_check_stage,      self.finalize_check_stage)

        self.add_event("next_target")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def change_status(self, status):
        for i in self.get_targets() + [self.cur_target]:
            if i is not None:
                i.change_status(status)

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

        return target

    def make_target(self, name, enable_scan):
        try:
            encsync_target = self.encsync.targets[name]
        except KeyError:
            raise ValueError("Unknown target: %r" % (name,))

        local = encsync_target["local"]
        remote = encsync_target["remote"]
        filename_encoding = encsync_target["filename_encoding"]
        
        target = SyncTarget(self, name, local, remote, filename_encoding)
        target.enable_scan = enable_scan

        return target

    def add_new_target(self, name, enable_scan, status="pending"):
        target = self.make_target(name, enable_scan)

        target.change_status(status)

        self.add_target(target)

        return target

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def set_speed_limit(self, limit):
        self.speed_limit = limit / float(self.n_workers)

        for worker in self.get_worker_list():
            worker.speed_limit = self.speed_limit

    def get_next_task(self):
        if self.stage["name"] in ("scan", "check"):
            return self.get_next_scannable()

        with self.task_lock:
            try:
                diff = next(self.diffs)
            except StopIteration:
                return

            task = SyncTask()
            task.parent = self.cur_target

            task.task_type, task.type, task.path = diff[:3]

            try:
                if task.task_type in ("new", "update") and task.type == "f":
                    size = os.path.getsize(Paths.to_sys(diff[2].local))
                    task.size = pad_size(size) + MIN_ENC_SIZE
            except FileNotFoundError:
                task.size = 0

            task.change_status("pending")

            return task

    def build_diffs_table(self):
        assert(self.cur_target is not None)

        self.cur_target.emit_event("diffs_started")

        diffs = FileComparator.compare_lists(self.encsync,
                                             self.cur_target.name,
                                             self.directory)
        
        try:
            self.difflist.begin_transaction()
            self.difflist.clear_differences(self.cur_target.local,
                                            self.cur_target.remote)
            self.difflist.insert_differences(diffs)
            self.difflist.commit()
        except BaseException as e:
            self.difflist.rollback()
            self.cur_target.emit_event("diffs_failed")
            raise e

        try:
            if self.cur_target.stage != "check":
                diff_count = self.difflist.get_difference_count(self.cur_target.local,
                                                                self.cur_target.remote)
                n_done = self.cur_target.get_n_done()

                self.cur_target.total_children = diff_count + n_done
        except BaseException as e:
            self.cur_target.emit_event("diffs_failed")
            raise e

        self.cur_target.emit_event("diffs_finished")

    def work(self):
        try:
            self.shared_duplist.create()
            self.difflist.create()
        except BaseException as e:
            self.emit_event("error", e)
            return

        while not self.stopped:
            try:
                with self.targets_lock:
                    if self.stopped or not len(self.targets):
                        break

                    target = self.targets.pop(0)
                    self.cur_target = target

                self.emit_event("next_target", target)

                if target.status == "suspended":
                    self.cur_target = None
                    continue

                target.change_status("pending")

                assert(self.stage is None)

                self.shared_llist = LocalFileList(target.name, self.directory)
                self.shared_rlist = RemoteFileList(target.name, self.directory)

                try:
                    if not self.enable_journal:
                        self.shared_llist.disable_journal()
                        self.shared_rlist.disable_journal()

                    self.shared_llist.create()
                    self.shared_rlist.create()
                except BaseException as e:
                    self.emit_event("error", e)
                    target.change_state("failed")
                    continue

                stages = self.stage_order

                if target.stage is not None:
                    # Skip completed stages
                    idx = self.stage_order.index(target.stage)
                    stages = self.stage_order[idx:]

                if target.stage is None and not target.enable_scan:
                    self.build_diffs_table()
                elif target.stage not in {None, "scan", "check"}:
                    self.build_diffs_table()

                for stage in stages:
                    if self.stopped or target.status in ("suspended", "failed"):
                        break

                    target.stage = stage

                    self.run_stage(stage)

                    self.reset_diffs()

                    if target.status == "suspended":
                        break

                if target.total_children == 0 and target.stage not in (None, "scan"):
                    target.change_status("finished")

                if target.status == "finished":
                    target.stage = None
                    self.difflist.clear_differences(target.local, target.remote)

                self.cur_target = None
            except BaseException as e:
                self.emit_event("error", e)
                if self.cur_target is not None:
                    self.cur_target.change_status("failed")

        assert(self.stage is None)

    def init_duplicates_stage(self):
        self.diffs = self.difflist.select_rmdup_differences(self.cur_target.remote)

        self.shared_duplist.begin_transaction()

        self.start_workers(self.n_workers, RmDupWorker, self)

    def finalize_duplicates_stage(self):
        self.shared_duplist.commit()

    def init_rm_stage(self):
        self.diffs = self.difflist.select_rm_differences(self.cur_target.local,
                                                         self.cur_target.remote)

        self.shared_llist.begin_transaction()
        self.shared_rlist.begin_transaction()

        self.start_workers(self.n_workers, RmWorker, self)

    def finalize_rm_stage(self):
        self.shared_llist.commit()
        self.shared_rlist.commit()

    def init_dirs_stage(self):
        self.diffs = self.difflist.select_dirs_differences(self.cur_target.local,
                                                           self.cur_target.remote)

        self.shared_llist.begin_transaction()
        self.shared_rlist.begin_transaction()

        self.start_worker(MkdirWorker, self)

    def finalize_dirs_stage(self):
        self.shared_llist.commit()
        self.shared_rlist.commit()

    def init_files_stage(self):
        self.diffs = self.difflist.select_files_differences(self.cur_target.local,
                                                            self.cur_target.remote)

        self.shared_llist.begin_transaction()
        self.shared_rlist.begin_transaction()

        self.start_workers(self.n_workers, UploadWorker, self)

    def finalize_files_stage(self):
        self.shared_llist.commit()
        self.shared_rlist.commit()

    def get_next_scannable(self):
        with self.scannables_lock:
            if len(self.scannables) > 0:
                return self.scannables.pop(0)

    def add_task(self, scannable):
        with self.scannables_lock:
            task = ScanTask(scannable)
            self.scannables.append(task)

            for worker in self.get_worker_list():
                worker.set_dirty()

    def wait_workers(self):
        workers = self.get_worker_list()

        while True:
            for worker in workers:
                worker.wait_idle()

            workers = self.get_worker_list()

            if all(worker.is_idle() for worker in workers):
                return

    def do_scan(self, scan_type):
        assert(scan_type in ("local", "remote"))

        if scan_type == "local":
            target = ScanTarget(scan_type, self.cur_target.name, self.cur_target.local)
            scannable = LocalScannable(target.path)
        elif scan_type == "remote":
            target = ScanTarget(scan_type, self.cur_target.name, self.cur_target.remote,
                                self.cur_target.filename_encoding)
            scannable = RemoteScannable(self.encsync, target.path,
                                        filename_encoding=target.filename_encoding)

        self.cur_target.emit_event("%s_scan" % scan_type, target)

        target.change_status("pending")

        filelist = {"local":  self.shared_llist,
                    "remote": self.shared_rlist}[scan_type]

        filelist.begin_transaction()

        try:
            filelist.remove_node_children(target.path)

            scannable.identify()

            if scan_type == "local":
                if scannable.type is None:
                    raise LocalPathNotFoundError("%r does not exist" % (scannable.path,),
                                                 scannable.path)
                    
                path = Paths.from_sys(scannable.path)
                if scannable.type == "d":
                    path = Paths.dir_normalize(path)

                if PathMatch.match(path, self.encsync.allowed_paths):
                    self.add_task(scannable)
                    filelist.insert_node(scannable.to_node())

                self.start_worker(LocalScanWorker, self, target)
            else:
                self.add_task(scannable)
                filelist.insert_node(scannable.to_node())

                self.start_workers(self.n_scan_workers, RemoteScanWorker, self, target)

                self.wait_workers()
                self.stop_workers()

            self.join_workers()
        except DiskNotFoundError:
            pass
        except BaseException as e:
            filelist.rollback()

            self.emit_event("error", e)

            target.change_status("failed")

            self.cur_target.emit_event("%s_scan_failed" % scan_type, target)
            if self.cur_target.status == "pending":
                self.cur_target.change_status("failed")

            return False

        if target.status == "pending" and self.cur_target.status == "pending":
            filelist.commit()
            target.change_status("finished")
            self.cur_target.emit_event("%s_scan_finished" % scan_type, target)

            return True
        else:
            filelist.rollback()
            target.change_status("failed")
            self.cur_target.emit_event("%s_scan_failed" % scan_type, target)
            if self.cur_target.status == "pending":
                self.cur_target.change_status("failed")

            return False

    def init_scan_stage(self):
        try:
            if not self.cur_target.enable_scan:
                return

            self.do_scan("local")

            if self.cur_target.status != "pending":
                return

            if self.shared_rlist.is_empty(self.cur_target.remote):
                self.do_scan("remote")
        except BaseException as e:
            self.emit_event("error", e)
            self.cur_target.change_status("failed")
            self.shared_llist.rollback()
            self.shared_rlist.rollback()
        finally:
            self.scannables.clear()

    def finalize_scan_stage(self):
        try:
            if not self.cur_target.enable_scan:
                return

            if self.cur_target.status != "pending" or self.stopped:
                return

            self.build_diffs_table()
        except BaseException as e:
            self.emit_event("error", e)
            self.cur_target.change_status("failed")

    def init_check_stage(self):
        try:
            if self.cur_target.skip_integrity_check:
                return

            self.cur_target.change_status("pending")

            self.cur_target.emit_event("integrity_check")

            self.do_scan("remote")
        except BaseException as e:
            self.emit_event("error", e)
            self.cur_target.change_status("failed")

    def finalize_check_stage(self):
        try:
            if self.cur_target.status != "pending" or self.stopped:
                return

            if self.cur_target.skip_integrity_check:
                return

            self.build_diffs_table()

            if self.difflist.get_difference_count(self.cur_target.local, self.cur_target.remote):
                self.cur_target.emit_event("integrity_check_failed")
                self.cur_target.change_status("failed")
            else:
                self.cur_target.emit_event("integrity_check_finished")
                self.cur_target.change_status("finished")
        except BaseException as e:
            self.emit_event("error", e)
            self.cur_target.change_status("failed")

    def reset_diffs(self):
        self.diffs = None
