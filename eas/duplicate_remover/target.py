# -*- coding: utf-8 -*-

import os
import shutil

from ..task import Task
from ..duplicate_list import DuplicateList
from ..constants import AUTOCOMMIT_INTERVAL
from ..worker import WorkerPool
from ..common import threadsafe_iterator
from .. import pathm
from .worker import DuplicateRemoverWorker
from .task import DuplicateRemoverTask

__all__ = ["DuplicateRemoverTarget"]

class DuplicateRemoverTarget(Task):
    """
        Events: autocommit_started, autocommit_failed, autocommit_finished
    """

    def __init__(self, duprem, storage_name, path):
        Task.__init__(self)

        self.duprem = duprem
        self.storage_name = storage_name
        self.config = duprem.config
        self.path = None
        self.prefix = None
        self.storage = None
        self.filename_encoding = None

        self.shared_duplist = None

        path = pathm.join_properly("/", path)
        self.path = path

        folder = self.config.identify_folder(storage_name, path)

        if folder is None:
            msg = "%r does not belong to any folders" % (storage_name + "://" + path,)
            raise ValueError(msg)

        if not folder["encrypted"]:
            raise ValueError("%r is not encrypted" % (storage_name + "://" + path,))

        self.filename_encoding = folder["filename_encoding"]
        self.prefix = folder["path"]

        self.preserve_modified = False

        self.n_workers = 1

        self.pool = WorkerPool(None)

    def stop(self):
        super().stop()

        self.pool.stop()

    def autocommit(self):
        if self.shared_duplist.time_since_last_commit() >= AUTOCOMMIT_INTERVAL:
            try:
                self.emit_event("autocommit_started", self.shared_duplist)
                self.shared_duplist.seamless_commit()
                self.emit_event("autocommit_finished", self.shared_duplist)
            except Exception as e:
                self.emit_event("autocommit_failed", self.shared_duplist)
                raise e

    @threadsafe_iterator
    def task_iterator(self, duplicates):
        while True:
            try:
                ivs, path = next(duplicates)[1:]
            except StopIteration:
                break

            task = DuplicateRemoverTask(self)
            task.storage = self.storage
            task.prefix = self.prefix
            task.filename_encoding = self.filename_encoding
            task.path = path
            task.ivs = ivs

            yield task

    def complete(self):
        if self.stopped:
            return True

        self.status = "pending"

        self.storage = self.config.storages[self.storage_name]

        self.shared_duplist = DuplicateList(self.storage.name, self.duprem.directory)

        if not self.duprem.enable_journal:
            self.shared_duplist.disable_journal()

        self.shared_duplist.create()

        if self.stopped:
            return True

        copy_src_path = self.shared_duplist.connection.path
        copy_dst_path = os.path.join(os.path.split(copy_src_path)[0], "duplist_copy.db")
        copy_duplist = None

        try:
            shutil.copyfile(copy_src_path, copy_dst_path)

            copy_duplist = DuplicateList(self.storage.name, self.duprem.directory,
                                         filename="duplist_copy.db")

            if self.stopped:
                return True

            self.expected_total_children = copy_duplist.get_file_count(self.path)
            duplicates = copy_duplist.find_recursively(self.path)

            if self.status == "pending" and self.total_children == 0:
                self.status = "finished"
                self.shared_duplist = None
                return True

            self.shared_duplist.begin_transaction()

            self.pool.clear()
            self.pool.queue = self.task_iterator(duplicates)

            if self.storage.parallelizable:
                n_workers = self.n_workers
            else:
                n_workers = 1

            try:
                self.pool.spawn_many(n_workers, DuplicateRemoverWorker, self.duprem)
                self.pool.join()
            finally:
                self.shared_duplist.commit()

            if self.status == "pending":
                if self.total_children == 0:
                    self.status = "finished"
                elif self.progress["skipped"] == self.total_children:
                    self.status = "skipped"
                elif self.progress["finished"] + self.progress["skipped"] == self.total_children:
                    self.status = "finished"
                elif self.progress["suspended"] > 0:
                    self.status = "suspended"
                elif self.progress["failed"] > 0:
                    self.status = "failed"
        finally:
            if copy_duplist is not None:
                copy_duplist.close()

            try:
                os.remove(copy_dst_path)
            except IOError:
                pass

        self.shared_duplist = None

        return True
