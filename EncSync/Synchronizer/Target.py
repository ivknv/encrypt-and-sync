#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Logging import TargetFailLogReceiver

from ..StagedTask import StagedTask
from ..Scanner import Scanner
from ..DuplicateRemover import DuplicateRemover
from ..DiffList import DiffList
from ..FolderStorage import get_folder_storage
from .. import FileComparator
from .Worker import SyncWorker
from .Tasks import UploadTask, MkdirTask, RmTask

__all__ = ["SyncTarget"]

COMMIT_INTERVAL = 7.5 * 60 # Seconds

class SyncTarget(StagedTask):
    """
        Events: integrity_check, integrity_check_failed, integrity_check_finished,
                diffs_started, diffs_failed, diffs_finished, autocommit_started,
                autocommit_failed, autocommit_finished
    """

    def __init__(self, synchronizer):
        StagedTask.__init__(self)

        self.synchronizer = synchronizer
        self.config = synchronizer.config
        self.src = None
        self.dst = None

        self.folder1 = None
        self.folder2 = None
        
        self.skip_integrity_check = False
        self.enable_scan = True
        self.avoid_src_rescan = False
        self.avoid_dst_rescan = False
        self.no_remove = False

        self.shared_flist1 = None
        self.shared_flist2 = None
        self.difflist = None
        self.differences = None

        self.tasks = []
        self.task_lock = threading.Lock()

        self.upload_limit = self.synchronizer.upload_limit
        self.download_limit = self.synchronizer.download_limit

        self.set_stage("scan",  self.init_scan,  self.finalize_scan)
        self.set_stage("rmdup", self.init_rmdup, self.finalize_rmdup)
        self.set_stage("rm",    self.init_rm,    self.finalize_rm)
        self.set_stage("dirs",  self.init_dirs,  self.finalize_dirs)
        self.set_stage("files", self.init_files, self.finalize_files)
        self.set_stage("check", self.init_check, self.finalize_check)

        self.add_receiver(TargetFailLogReceiver())

    def get_n_done(self):
        return self.progress["finished"] + self.progress["failed"] + self.progress["skipped"]

    def stop_condition(self):
        if self.stopped or self.synchronizer.stopped:
            return True

        return self.status not in (None, "pending")

    def autocommit(self):
        try:
            if self.shared_flist1.time_since_last_commit() >= COMMIT_INTERVAL:
                self.emit_event("autocommit_started", self.shared_flist1)
                self.shared_flist1.seamless_commit()
                self.emit_event("autocommit_finished", self.shared_flist1)
        except Exception as e:
            self.emit_event("autocommit_failed", self.shared_flist1)
            raise e

        try:
            if self.shared_flist2.time_since_last_commit() >= COMMIT_INTERVAL:
                self.emit_event("autocommit_started", self.shared_flist2)
                self.shared_flist2.seamless_commit()
                self.emit_event("autocommit_finished", self.shared_flist2)
        except Exception as e:
            self.emit_event("autocommit_failed", self.shared_flist2)
            raise e

    def get_differences(self):
        return FileComparator.compare_lists(self.config,
                                            self.folder1["name"],
                                            self.folder2["name"],
                                            self.synchronizer.directory)

    def build_diffs_table(self):
        self.emit_event("diffs_started")

        diffs = self.get_differences()
        
        try:
            self.difflist.begin_transaction()
            self.difflist.clear_differences(self.folder1["name"], self.folder2["name"])

            with self.difflist:
                for diff in diffs:
                    if not (self.no_remove and diff["type"] == "rm"):
                        self.difflist.insert_difference(diff)

            self.difflist.commit()
        except Exception as e:
            self.difflist.rollback()
            self.emit_event("diffs_failed")
            raise e

        try:
            if self.stage != "check":
                diff_count = self.difflist.get_difference_count(self.folder1["name"], self.folder2["name"])
                n_done = self.get_n_done()

                self.expected_total_children = diff_count + n_done
        except Exception as e:
            self.emit_event("diffs_failed")
            raise e

        self.emit_event("diffs_finished")

    def get_next_task(self):
        with self.task_lock:
            try:
                diff = next(self.differences)
            except StopIteration:
                return

            assert(diff["type"] in ("new", "update", "rm"))
            assert(diff["node_type"] in ("f", "d"))

            if diff["type"] == "new":
                if diff["node_type"] == "f":
                    task = UploadTask(self)
                elif diff["node_type"] == "d":
                    task = MkdirTask(self)
            elif diff["type"] == "update":
                task = UploadTask(self)
            elif diff["type"] == "rm":
                task = RmTask(self)

            task.type = diff["type"]
            task.node_type = diff["node_type"]
            task.path = diff["path"]
            task.upload_limit = self.upload_limit
            task.download_limit = self.download_limit

            return task

    def do_scan(self, *folder_names, force=False):
        scanner = Scanner(self.config,
                          self.synchronizer.directory,
                          self.synchronizer.n_scan_workers,
                          self.synchronizer.enable_journal)
        targets = []

        for folder_name in folder_names:
            assert(folder_name in (self.folder1["name"], self.folder2["name"]))

            target = scanner.make_target(folder_name)

            if folder_name == self.folder1["name"]:
                rescan = force or not self.avoid_src_rescan

                if rescan or self.shared_flist1.is_empty(self.src.prefix):
                    scanner.add_target(target)
                    targets.append(target)
            else:
                rescan = force or not self.avoid_dst_rescan

                if rescan or self.shared_flist2.is_empty(self.dst.prefix):
                    scanner.add_target(target)
                    targets.append(target)

        if not targets or self.stop_condition():
            return

        self.synchronizer.start_worker(scanner).join()

        if self.stop_condition():
            return

        if any(i.status != "finished" for i in targets):
            self.status = "failed"

    def init_scan(self):
        if not self.enable_scan:
            return

        if self.stop_condition():
            return

        self.do_scan(self.folder1["name"], self.folder2["name"])

    def finalize_scan(self):
        if not self.enable_scan:
            return

        if self.stop_condition():
            return

        self.build_diffs_table()

    def init_rmdup(self):
        duprem = DuplicateRemover(self.config,
                                  self.synchronizer.directory,
                                  self.synchronizer.n_workers,
                                  self.synchronizer.enable_journal)

        if self.src.encrypted:
            duprem.add_new_target(self.src.storage.name, self.src.prefix)

        if self.dst.encrypted:
            duprem.add_new_target(self.dst.storage.name, self.dst.prefix)

        if self.stop_condition():
            return

        self.synchronizer.start_worker(duprem).join()

    def finalize_rmdup(self):
        pass

    def init_rm(self):
        if self.no_remove:
            return

        self.differences = self.difflist.select_rm_differences(self.folder1["name"], self.folder2["name"])

        self.shared_flist1.begin_transaction()
        self.shared_flist2.begin_transaction()

        self.synchronizer.start_workers(self.synchronizer.n_workers,
                                        SyncWorker, self.synchronizer)
        self.synchronizer.join_workers()

    def finalize_rm(self):
        if self.no_remove:
            return

        self.shared_flist2.clear_deleted()
        self.shared_flist2.commit()

        self.shared_flist1.clear_deleted()
        self.shared_flist1.commit()

    def init_dirs(self):
        self.differences = self.difflist.select_dirs_differences(self.folder1["name"], self.folder2["name"])

        self.shared_flist1.begin_transaction()
        self.shared_flist2.begin_transaction()

        self.synchronizer.start_worker(SyncWorker, self.synchronizer).join()

    def finalize_dirs(self):
        self.shared_flist1.commit()
        self.shared_flist2.commit()

    def init_files(self):
        self.differences = self.difflist.select_files_differences(self.folder1["name"], self.folder2["name"])

        self.shared_flist1.begin_transaction()
        self.shared_flist2.begin_transaction()

        self.synchronizer.start_workers(self.synchronizer.n_workers,
                                        SyncWorker, self.synchronizer)
        self.synchronizer.join_workers()

    def finalize_files(self):
        self.shared_flist1.commit()
        self.shared_flist2.commit()

    def init_check(self):
        if self.skip_integrity_check:
            return

        if self.stop_condition():
            return

        self.emit_event("integrity_check")

        self.do_scan(self.folder2["name"], force=True)

    def finalize_check(self):
        if self.stop_condition():
            return

        if self.skip_integrity_check:
            return

        self.build_diffs_table()

        if self.difflist.get_difference_count(self.folder1["name"], self.folder2["name"]):
            self.emit_event("integrity_check_failed")
            self.status = "failed"
        else:
            self.emit_event("integrity_check_finished")
            self.status = "finished"

    def complete(self, worker):
        if self.stop_condition():
            return True

        self.status = "pending"

        try:
            self.difflist = DiffList(self.synchronizer.directory)

            self.src = get_folder_storage(self.folder1["type"])(self.folder1["name"],
                                                                self.config,
                                                                self.synchronizer.directory)
            self.dst = get_folder_storage(self.folder2["type"])(self.folder2["name"],
                                                                self.config,
                                                                self.synchronizer.directory)

            self.shared_flist1 = self.src.filelist
            self.shared_flist2 = self.dst.filelist

            if not self.synchronizer.enable_journal:
                self.shared_flist1.disable_journal()
                self.shared_flist2.disable_journal()
                self.difflist.disable_journal()

            self.shared_flist1.create()
            self.shared_flist2.create()
            self.difflist.create()

            stages = ("scan", "rmdup", "rm", "dirs", "files", "check")

            if self.stage is not None:
                # Skip completed stages
                idx = stages.index(self.stage)
                stages = stages[idx:]

            if self.stage is None and not self.enable_scan:
                self.build_diffs_table()
            elif self.stage not in {None, "scan", "check"}:
                self.build_diffs_table()

            if self.total_children == 0 and self.stage not in (None, "scan"):
                self.status = "finished"
                return True

            for stage in stages:
                if self.stop_condition():
                    return

                self.run_stage(stage)

                self.differences = None

            if self.status == "pending":
                if self.progress["finished"] + self.progress["skipped"] == self.total_children:
                    self.status = "finished"
                elif self.progress["suspended"] > 0:
                    self.status = "suspended"
                elif self.progress["failed"] > 0:
                    self.status = "failed"

            if self.status == "finished":
                self.difflist.clear_differences(self.folder1["name"], self.folder2["name"])
        finally:
            self.differences = None
            self.difflist = None
            self.shared_flist1 = None
            self.shared_flist2 = None
