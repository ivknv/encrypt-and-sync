# -*- coding: utf-8 -*-

import os
import shutil
import threading

from ..Task import Task
from ..FileList import DuplicateList
from .Worker import DuplicateRemoverWorker
from .Task import DuplicateRemoverTask

__all__ = ["DuplicateRemoverTarget"]

COMMIT_INTERVAL = 7.5 * 60 # Seconds

class DuplicateRemoverTarget(Task):
    """
        Events: autocommit_started, autocommit_failed, autocommit_finished
    """

    def __init__(self, duprem, storage_name):
        Task.__init__(self)

        self.duprem = duprem
        self.storage_name = storage_name
        self.config = duprem.config
        self.path = None
        self.prefix = None
        self.storage = None
        self.filename_encoding = None

        self.shared_duplist = None
        self.duplicates = None
        self.task_lock = threading.Lock()

    def stop_condition(self):
        if self.stopped or self.duprem.stopped:
            return True

        return self.status not in (None, "pending")

    def autocommit(self):
        if self.shared_duplist.time_since_last_commit() >= COMMIT_INTERVAL:
            try:
                self.emit_event("autocommit_started", self.shared_duplist)
                self.shared_duplist.seamless_commit()
                self.emit_event("autocommit_finished", self.shared_duplist)
            except Exception as e:
                self.emit_event("autocommit_failed", self.shared_duplist)
                raise e

    def get_next_task(self):
        with self.task_lock:
            try:
                task = DuplicateRemoverTask(self)
                task.storage = self.storage
                task.prefix = self.prefix
                task.ivs, task.path = next(self.duplicates)[1:]
                task.filename_encoding = self.filename_encoding

                return task
            except StopIteration:
                pass

    def complete(self, worker):
        if self.stop_condition():
            return True

        self.storage = self.config.storages[self.storage_name]

        self.shared_duplist = DuplicateList(self.storage.name, self.duprem.directory)

        if not self.duprem.enable_journal:
            self.shared_duplist.disable_journal()

        self.shared_duplist.create()

        if self.stop_condition():
            return True

        copy_src_path = self.shared_duplist.connection.path
        copy_dst_path = os.path.join(os.path.split(copy_src_path)[0], "duplist_copy.db")
        copy_duplist = None

        try:
            shutil.copyfile(copy_src_path, copy_dst_path)

            copy_duplist = DuplicateList(self.storage.name, self.duprem.directory,
                                         filename="duplist_copy.db")

            if self.stop_condition():
                return True

            self.expected_total_children = copy_duplist.get_children_count(self.path)
            self.duplicates = copy_duplist.find_children(self.path)

            if self.status == "pending" and self.total_children == 0:
                self.status = "finished"
                self.duplicates = None
                self.shared_duplist = None
                return True

            if self.storage.parallelizable:
                n = self.duprem.n_workers
            else:
                n = 1

            self.shared_duplist.begin_transaction()

            try:
                self.duprem.start_workers(n, DuplicateRemoverWorker, self.duprem)
                self.duprem.join_workers()
            finally:
                self.shared_duplist.commit()

            if self.status == "pending":
                if self.progress["finished"] + self.progress["skipped"] == self.total_children:
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

        self.duplicates = None
        self.shared_duplist = None

        return True
