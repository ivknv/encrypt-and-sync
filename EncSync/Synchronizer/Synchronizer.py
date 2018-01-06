#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Workers import UploadWorker, MkdirWorker, RmWorker
from .Task import SyncTask
from .Target import SyncTarget
from .Logging import logger
from ..Scanner import Scanner
from ..DuplicateRemover import DuplicateRemover
from ..Worker import StagedWorker
from ..LogReceiver import LogReceiver
from ..DiffList import DiffList
from ..TargetStorage import get_target_storage
from .. import FileComparator

__all__ = ["Synchronizer"]

class Synchronizer(StagedWorker):
    def __init__(self, encsync, directory, n_workers=2, n_scan_workers=2,
                 enable_journal=True):
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

        self.shared_flist1 = None
        self.shared_flist2 = None
        self.difflist = DiffList(self.encsync, self.directory)

        self.stage_order = ("scan", "rmdup", "rm", "dirs", "files", "check")

        self.add_stage("scan",  self.init_scan_stage,  self.finalize_scan_stage)
        self.add_stage("rmdup", self.init_rmdup_stage, self.finalize_rmdup_stage)
        self.add_stage("rm",    self.init_rm_stage,    self.finalize_rm_stage)
        self.add_stage("dirs",  self.init_dirs_stage,  self.finalize_dirs_stage)
        self.add_stage("files", self.init_files_stage, self.finalize_files_stage)
        self.add_stage("check", self.init_check_stage, self.finalize_check_stage)

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
        
        target = SyncTarget()
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

    def get_next_task(self):
        with self.task_lock:
            try:
                diff = next(self.diffs)
            except StopIteration:
                return

            task = SyncTask()
            task.parent = self.cur_target

            task.type = diff["type"]
            task.node_type = diff["node_type"]
            task.path = diff["path"]

            task.status = "pending"

            return task

    def build_diffs_table(self):
        assert(self.cur_target is not None)

        self.cur_target.emit_event("diffs_started")

        diffs = FileComparator.compare_lists(self.encsync,
                                             self.cur_target.name,
                                             self.directory)
        
        try:
            self.difflist.begin_transaction()
            self.difflist.clear_differences(self.cur_target.name)
            self.difflist.insert_differences(diffs)
            self.difflist.commit()
        except Exception as e:
            self.difflist.rollback()
            self.cur_target.emit_event("diffs_failed")
            raise e

        try:
            if self.cur_target.stage != "check":
                diff_count = self.difflist.get_difference_count(self.cur_target.name)
                n_done = self.cur_target.get_n_done()

                self.cur_target.total_children = diff_count + n_done
        except Exception as e:
            self.cur_target.emit_event("diffs_failed")
            raise e

        self.cur_target.emit_event("diffs_finished")

    def work(self):
        assert(self.n_workers >= 1)

        try:
            if not self.enable_journal:
                self.difflist.disable_journal()

            self.difflist.create()
        except Exception as e:
            self.emit_event("error", e)
            return

        while not self.stopped:
            with self.targets_lock:
                if self.stopped or not self.targets:
                    break

                target = self.targets.pop(0)
                self.cur_target = target

            try:
                self.emit_event("next_target", target)

                if target.status == "suspended":
                    self.cur_target = None
                    continue

                target.status = "pending"

                assert(self.stage is None)

                self.shared_flist1 = target.src.filelist
                self.shared_flist2 = target.dst.filelist

                try:
                    if not self.enable_journal:
                        self.shared_flist1.disable_journal()
                        self.shared_flist2.disable_journal()

                    self.shared_flist1.create()
                    self.shared_flist2.create()
                except Exception as e:
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

                if target.total_children == 0 and target.stage not in (None, "scan"):
                    target.status = "finished"

                for stage in stages:
                    if self.stopped or target.status in ("suspended", "failed"):
                        break

                    target.stage = stage

                    self.run_stage(stage)

                    self.diffs = None

                    if target.status == "suspended":
                        break

                if target.status == "pending":
                    if target.progress["finished"] == target.total_children:
                        target.status = "finished"
                    elif target.progress["suspended"] > 0:
                        target.status = "suspended"
                    elif target.progress["failed"] > 0:
                        target.status = "failed"

                if target.status == "finished":
                    target.stage = None
                    self.difflist.clear_differences(target.name)

                self.cur_target = None
            except Exception as e:
                self.emit_event("error", e)
                if self.cur_target is not None:
                    self.cur_target.status = "failed"

        assert(self.stage is None)

    def init_rmdup_stage(self):
        try:
            duprem = DuplicateRemover(self.encsync, self.directory,
                                      self.n_workers, self.enable_journal)

            if self.cur_target.src.encrypted:
                duprem.add_new_target(self.cur_target.src.storage.name,
                                      self.cur_target.src.prefix)

            if self.cur_target.dst.encrypted:
                duprem.add_new_target(self.cur_target.dst.storage.name,
                                      self.cur_target.dst.prefix)

            if self.stopped or self.cur_target.status != "pending":
                return

            self.start_worker(duprem).join()
        except Exception as e:
            self.emit_event("error", e)

    def finalize_rmdup_stage(self):
        pass

    def init_rm_stage(self):
        self.diffs = self.difflist.select_rm_differences(self.cur_target.name)

        self.shared_flist1.begin_transaction()
        self.shared_flist2.begin_transaction()

        self.start_workers(self.n_workers, RmWorker, self)

    def finalize_rm_stage(self):
        self.shared_flist1.commit()
        self.shared_flist2.commit()

    def init_dirs_stage(self):
        self.diffs = self.difflist.select_dirs_differences(self.cur_target.name)

        self.shared_flist1.begin_transaction()
        self.shared_flist2.begin_transaction()

        self.start_worker(MkdirWorker, self)

    def finalize_dirs_stage(self):
        self.shared_flist1.commit()
        self.shared_flist2.commit()

    def init_files_stage(self):
        self.diffs = self.difflist.select_files_differences(self.cur_target.name)

        self.shared_flist1.begin_transaction()
        self.shared_flist2.begin_transaction()

        self.start_workers(self.n_workers, UploadWorker, self)

    def finalize_files_stage(self):
        self.shared_flist1.commit()
        self.shared_flist2.commit()

    def do_scan(self, *scan_types, force=False):
        scanner = Scanner(self.encsync, self.directory,
                          self.n_scan_workers, self.enable_journal)
        targets = []

        for scan_type in scan_types:
            assert(scan_type in ("src", "dst"))

            target = scanner.make_target(scan_type, self.cur_target.name)

            if scan_type == "src":
                scanner.add_target(target)
                targets.append(target)
            elif force or self.shared_flist2.is_empty(self.cur_target.dst.prefix):
                scanner.add_target(target)
                targets.append(target)

        if self.stopped or self.cur_target.status != "pending":
            return

        self.start_worker(scanner).join()

        if any(i.status != "finished" for i in targets):
            self.cur_target.status = "failed"

    def init_scan_stage(self):
        try:
            if not self.cur_target.enable_scan:
                return

            if self.stopped or self.cur_target.status != "pending":
                return

            self.do_scan("src", "dst")
        except Exception as e:
            self.emit_event("error", e)
            self.cur_target.status = "failed"

    def finalize_scan_stage(self):
        try:
            if not self.cur_target.enable_scan:
                return

            if self.cur_target.status != "pending" or self.stopped:
                return

            self.build_diffs_table()
        except Exception as e:
            self.emit_event("error", e)
            self.cur_target.status = "failed"

    def init_check_stage(self):
        try:
            if self.cur_target.skip_integrity_check:
                return

            if self.stopped or self.cur_target.status != "pending":
                return

            self.cur_target.emit_event("integrity_check")

            self.do_scan("dst", force=True)
        except Exception as e:
            self.emit_event("error", e)
            self.cur_target.status = "failed"

    def finalize_check_stage(self):
        try:
            if self.cur_target.status != "pending" or self.stopped:
                return

            if self.cur_target.skip_integrity_check:
                return

            self.build_diffs_table()

            if self.difflist.get_difference_count(self.cur_target.name):
                self.cur_target.emit_event("integrity_check_failed")
                self.cur_target.status = "failed"
            else:
                self.cur_target.emit_event("integrity_check_finished")
                self.cur_target.status = "finished"
        except Exception as e:
            self.emit_event("error", e)
            self.cur_target.status = "failed"
