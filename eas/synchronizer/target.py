# -*- coding: utf-8 -*-

from .logging import TargetFailLogReceiver

from ..staged_task import StagedTask
from ..scanner import Scanner, ScanTarget
from ..duplicate_remover import DuplicateRemover, DuplicateRemoverTarget
from ..difflist import DiffList
from ..duplicate_list import DuplicateList
from ..folder_storage import get_folder_storage
from ..constants import AUTOCOMMIT_INTERVAL
from ..worker import WorkerPool, get_current_worker
from ..common import threadsafe_iterator, recognize_path
from .. import pathm, file_comparator
from .worker import SyncWorker
from .tasks import UploadTask, MkdirTask, RmTask, ModifiedTask
from .tasks import ChmodTask, ChownTask, CreateSymlinkTask

__all__ = ["SyncTarget"]

class SyncTarget(StagedTask):
    """
        Events: integrity_check, integrity_check_failed, integrity_check_finished,
                diffs_started, diffs_failed, diffs_finished, autocommit_started,
                autocommit_failed, autocommit_finished
    """

    def __init__(self, synchronizer, path1, path2,
                 enable_scan, skip_integrity_check=False):
        StagedTask.__init__(self)

        self.synchronizer = synchronizer
        self.config = synchronizer.config
        self.src = None
        self.dst = None

        self.folder1 = None
        self.folder2 = None

        self.path1, self.path_type1 = recognize_path(path1)
        self.path2, self.path_type2 = recognize_path(path2)

        self.path1 = pathm.join_properly("/", self.path1)
        self.path2 = pathm.join_properly("/", self.path2)

        self.path1_with_proto = "%s://%s" % (self.path_type1, self.path1)
        self.path2_with_proto = "%s://%s" % (self.path_type2, self.path2)

        self.folder1 = self.config.identify_folder(self.path_type1, self.path1)
        self.folder2 = self.config.identify_folder(self.path_type2, self.path2)

        if self.folder1 is None:
            raise KeyError("%r does not belong to any known folders" % (path1,))

        if self.folder2 is None:
            raise KeyError("%r does not belong to any known folders" % (path2,))

        self.subpath1 = pathm.cut_prefix(self.path1, self.folder1["path"])
        self.subpath2 = pathm.cut_prefix(self.path2, self.folder2["path"])

        self.subpath1 = pathm.join_properly("/", self.subpath1)
        self.subpath2 = pathm.join_properly("/", self.subpath2)

        self.skip_integrity_check = False
        self.enable_scan = True
        self.avoid_src_rescan = False
        self.avoid_dst_rescan = False
        self.no_remove = False

        self.shared_flist1 = None
        self.shared_flist2 = None
        self.difflist = None

        self.n_workers = 1
        self.n_scan_workers = 1

        self.upload_limit = synchronizer.upload_limit
        self.download_limit = synchronizer.download_limit

        self.enable_scan = enable_scan
        self.skip_integrity_check = skip_integrity_check
        self.avoid_src_rescan = self.folder1["avoid_rescan"]
        self.avoid_dst_rescan = self.folder2["avoid_rescan"]
        self.sync_modified = False
        self.sync_mode = False
        self.sync_ownership = False
        self.force_scan = False

        self.pool = WorkerPool(None)

        self.duprem = DuplicateRemover(self.config,
                                       synchronizer.directory,
                                       synchronizer.enable_journal)
        self.scanner = Scanner(self.config,
                               synchronizer.directory,
                               synchronizer.enable_journal)

        self.set_stage("scan",     self.init_scan,     self.finalize_scan)
        self.set_stage("rmdup",    self.init_rmdup,    self.finalize_rmdup)
        self.set_stage("rm",       self.init_rm,       self.finalize_rm)
        self.set_stage("dirs",     self.init_dirs,     self.finalize_dirs)
        self.set_stage("files",    self.init_files,    self.finalize_files)
        self.set_stage("metadata", self.init_metadata, self.finalize_metadata)
        self.set_stage("check",    self.init_check,    self.finalize_check)

        self.add_receiver(TargetFailLogReceiver())

    def get_n_done(self):
        return self.progress["finished"] + self.progress["failed"] + self.progress["skipped"]

    def stop(self):
        super().stop()

        self.pool.stop()

        self.scanner.stop()
        self.duprem.stop()

    def autocommit(self):
        try:
            if self.shared_flist1.time_since_last_commit() >= AUTOCOMMIT_INTERVAL:
                self.emit_event("autocommit_started", self.shared_flist1)
                self.shared_flist1.seamless_commit()
                self.emit_event("autocommit_finished", self.shared_flist1)

            if self.shared_flist2.time_since_last_commit() >= AUTOCOMMIT_INTERVAL:
                self.emit_event("autocommit_started", self.shared_flist2)
                self.shared_flist2.seamless_commit()
                self.emit_event("autocommit_finished", self.shared_flist2)
        except Exception as e:
            self.emit_event("autocommit_failed", self.shared_flist2)
            raise e

    def get_differences(self):
        return file_comparator.compare_lists(self.config,
                                             self.path1_with_proto,
                                             self.path2_with_proto,
                                             self.synchronizer.directory)

    def build_diffs_table(self, diff_types=None):
        self.emit_event("diffs_started")

        if diff_types is None:
            diff_types = {"rm", "new", "update", "modified", "chmod", "chown"}
        else:
            diff_types = set(diff_types)

        diffs = self.get_differences()

        if self.no_remove:
            diff_types.discard("rm")

        if not self.sync_modified or not self.dst.storage.supports_set_modified:
            diff_types.discard("modified")

        if not self.sync_mode or not self.dst.storage.supports_chmod:
            diff_types.discard("chmod")

        if not self.sync_ownership or not self.dst.storage.supports_chown:
            diff_types.discard("chown")

        try:
            self.difflist.begin_transaction()
            self.difflist.remove(self.path1_with_proto, self.path2_with_proto)

            with self.difflist:
                for diff in diffs:
                    if diff["type"] not in diff_types:
                        continue

                    self.difflist.insert(diff)

            self.difflist.commit()
        except Exception as e:
            self.difflist.rollback()
            self.emit_event("diffs_failed")
            raise e

        try:
            if self.stage != "check":
                diff_count = self.difflist.get_difference_count(self.path1_with_proto,
                                                                self.path2_with_proto)
                n_done = self.get_n_done()

                self.expected_total_children = diff_count + n_done
        except Exception as e:
            self.emit_event("diffs_failed")
            raise e

        self.emit_event("diffs_finished")

    @threadsafe_iterator
    def task_iterator(self, differences):
        while True:
            try:
                diff = next(differences)
            except StopIteration:
                break

            assert(diff["type"] in ("new", "update", "rm", "modified", "chmod", "chown"))
            assert(diff["node_type"] in ("f", "d"))

            if diff["type"] == "new":
                if diff["node_type"] == "f":
                    if diff["link_path"] is not None:
                        task = CreateSymlinkTask(self)
                    else:
                        task = UploadTask(self)
                elif diff["node_type"] == "d":
                    task = MkdirTask(self)
            elif diff["type"] == "update":
                task = UploadTask(self)
            elif diff["type"] == "rm":
                task = RmTask(self)
            elif diff["type"] == "modified":
                task = ModifiedTask(self)
            elif diff["type"] == "chmod":
                task = ChmodTask(self)
            elif diff["type"] == "chown":
                task = ChownTask(self)

            task.type = diff["type"]
            task.node_type = diff["node_type"]
            task.path = diff["path"]
            task.link_path = diff["link_path"]
            task.modified = diff["modified"]
            task.mode = diff["mode"]
            task.owner = diff["owner"]
            task.group = diff["group"]
            task.upload_limit = self.upload_limit
            task.download_limit = self.download_limit

            yield task

    def do_scan(self, *paths, force=False):
        targets = []

        for path in paths:
            target = ScanTarget(self.scanner, path)
            target.n_workers = self.n_scan_workers

            if target.name == self.folder1["name"]:
                rescan = force or not self.avoid_src_rescan

                if rescan or self.shared_flist1.is_empty(self.src.prefix):
                    self.scanner.add_target(target)
                    targets.append(target)
            else:
                rescan = force or not self.avoid_dst_rescan

                if rescan or self.shared_flist2.is_empty(self.dst.prefix):
                    self.scanner.add_target(target)
                    targets.append(target)

        if not targets or self.stopped:
            return

        self.scanner.run()

        if self.stopped:
            return

        if any(i.status != "finished" for i in targets):
            self.status = "failed"

    def init_scan(self):
        if not self.enable_scan and not self.force_scan:
            return

        if self.stopped:
            return

        self.do_scan(self.path1_with_proto, self.path2_with_proto, force=self.force_scan)

    def finalize_scan(self):
        if not self.enable_scan:
            return

        if self.stopped:
            return

        self.build_diffs_table()

    def init_rmdup(self):
        if self.src.encrypted:
            src_duplist = DuplicateList(self.src.storage.name, self.synchronizer.directory)

            if src_duplist.get_file_count(self.path1):
                target = DuplicateRemoverTarget(self.duprem, self.src.storage.name, self.path1)
                target.n_workers = self.n_workers
                target.preserve_modified = self.sync_modified
                self.duprem.add_target(target)

        if self.dst.encrypted:
            dst_duplist = DuplicateList(self.dst.storage.name, self.synchronizer.directory)

            if dst_duplist.get_file_count(self.path2):
                target = DuplicateRemoverTarget(self.duprem, self.dst.storage.name, self.path2)
                target.n_workers = self.n_workers
                target.preserve_modified = self.sync_modified
                self.duprem.add_target(target)

        if self.stopped:
            return

        if self.duprem.get_target_list():
            self.duprem.run()

    def finalize_rmdup(self):
        pass

    def init_rm(self):
        if self.no_remove:
            return

        differences = self.difflist.find_rm(self.path1_with_proto,
                                            self.path2_with_proto)

        self.shared_flist2.begin_transaction()

        if self.src.storage.parallelizable or self.dst.storage.parallelizable:
            n_workers = self.n_workers
        else:
            n_workers = 1

        self.pool.clear()
        self.pool.queue = self.task_iterator(differences)
        self.pool.spawn_many(n_workers, SyncWorker, self.synchronizer)
        self.pool.join()

    def finalize_rm(self):
        if self.no_remove:
            return

        self.shared_flist2.commit()

    def init_dirs(self):
        differences = self.difflist.find_dirs(self.path1_with_proto,
                                              self.path2_with_proto)

        self.shared_flist2.begin_transaction()

        self.pool.clear()
        self.pool.queue = self.task_iterator(differences)
        self.pool.spawn(SyncWorker, self.synchronizer)
        self.pool.join()

    def finalize_dirs(self):
        self.shared_flist2.commit()

    def init_files(self):
        differences = self.difflist.find_files(self.path1_with_proto,
                                               self.path2_with_proto)

        self.shared_flist1.begin_transaction()
        self.shared_flist2.begin_transaction()

        if self.src.storage.parallelizable or self.dst.storage.parallelizable:
            n_workers = self.n_workers
        else:
            n_workers = 1

        self.pool.clear()
        self.pool.queue = self.task_iterator(differences)
        self.pool.spawn_many(n_workers, SyncWorker, self.synchronizer)
        self.pool.join()

    def finalize_files(self):
        self.shared_flist1.commit()
        self.shared_flist2.commit()

    def init_metadata(self):
        self.build_diffs_table(("modified", "chmod", "chown"))

        differences = self.difflist.find_metadata(self.path1_with_proto,
                                                  self.path2_with_proto)

        self.shared_flist2.begin_transaction()

        if self.dst.storage.parallelizable:
            n_workers = self.n_workers
        else:
            n_workers = 1

        self.pool.clear()
        self.pool.queue = self.task_iterator(differences)
        self.pool.spawn_many(n_workers, SyncWorker, self.synchronizer)
        self.pool.join()

    def finalize_metadata(self):
        self.shared_flist2.commit()

    def init_check(self):
        if self.skip_integrity_check:
            return

        if self.stopped:
            return

        self.emit_event("integrity_check")

        self.do_scan(self.path2_with_proto, force=True)

    def finalize_check(self):
        if self.stopped:
            return

        if self.skip_integrity_check:
            return

        self.build_diffs_table()

        if self.difflist.get_difference_count(self.path1_with_proto,
                                              self.path2_with_proto):
            self.emit_event("integrity_check_failed")
            self.status = "failed"
        else:
            self.emit_event("integrity_check_finished")
            self.status = "finished"

    def complete(self):
        if self.stopped:
            return True

        self.status = "pending"

        worker = get_current_worker()

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

            stages = ("scan", "rmdup", "rm", "dirs", "files", "metadata", "check")

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
                if self.stopped:
                    return

                self.run_stage(stage)

            if self.status == "pending":
                if self.progress["skipped"] == self.total_children:
                    self.status = "skipped"
                elif self.progress["finished"] + self.progress["skipped"] == self.total_children:
                    self.status = "finished"
                elif self.progress["suspended"] > 0:
                    self.status = "suspended"
                elif self.progress["failed"] > 0:
                    self.status = "failed"

            if self.status == "finished":
                self.difflist.remove(self.path1_with_proto, self.path2_with_proto)
        finally:
            self.difflist = None
            self.shared_flist1 = None
            self.shared_flist2 = None
