# -*- coding: utf-8 -*-

import threading

from .. import Paths
from ..Worker import Worker
from ..FileList import DuplicateList
from ..LogReceiver import LogReceiver
from .Logging import logger
from .Worker import DuplicateRemoverWorker
from .Target import DuplicateRemoverTarget
from .Task import DuplicateRemoverTask

__all__ = ["DuplicateRemover"]

class DuplicateRemover(Worker):
    def __init__(self, encsync, directory, n_workers=2, enable_journal=True):
        Worker.__init__(self)

        self.encsync = encsync
        self.directory = directory
        self.n_workers = n_workers
        self.enable_journal = enable_journal

        self.targets = []
        self.targets_lock = threading.Lock()
        self.cur_target = None

        self.shared_duplist = None
        self.duplicates = None
        self.task_lock = threading.Lock()

        self.add_event("next_target")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def change_status(self, status):
        for target in self.get_targets() + [self.cur_target]:
            if target is not None:
                target.status = status

    def make_target(self, storage_name, path):
        path = Paths.join_properly("/", path)
        target = DuplicateRemoverTarget()
        target.path = path
        target.storage = self.encsync.storages[storage_name]

        encsync_target, dir_type = self.encsync.identify_target(storage_name, path)

        if encsync_target is None:
            msg = "%r does not belong to any targets" % (storage_name + "://" + path,)
            raise ValueError(msg)

        if not encsync_target[dir_type]["encrypted"]:
            raise ValueError("%r is not encrypted" % (storage_name + "://" + path,))

        encoding = encsync_target[dir_type]["filename_encoding"]
        target.filename_encoding = encoding
        target.prefix = encsync_target[dir_type]["path"]

        return target

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

            return target

    def add_new_target(self, storage_name, path):
        return self.add_target(self.make_target(storage_name, path))

    def get_next_task(self):
        with self.task_lock:
            try:
                task = DuplicateRemoverTask()
                task.parent = self.cur_target
                task.storage = self.cur_target.storage
                task.prefix = self.cur_target.prefix
                task.ivs, task.path = next(self.duplicates)[1:]
                task.filename_encoding = self.cur_target.filename_encoding

                return task
            except StopIteration:
                pass

    def work(self):
        while not self.stopped:
            with self.targets_lock:
                try:
                    target = self.targets.pop(0)
                    self.cur_target = target
                except IndexError:
                    break

            try:
                if self.stopped:
                    break

                self.emit_event("next_target", target)

                if self.stopped:
                    break

                if target.status is None:
                    target.status = "pending"

                if target.status == "suspended":
                    continue

                if self.stopped:
                    return

                try:
                    self.shared_duplist = DuplicateList(target.storage.name, self.directory)

                    if not self.enable_journal:
                        self.shared_duplist.disable_journal()

                    self.shared_duplist.create()
                except Exception as e:
                    self.emit_event("error", e)
                    target.status = "failed"
                    self.shared_duplist = None
                    self.cur_target = None
                    continue

                if self.stopped:
                    return

                self.shared_duplist.begin_transaction()

                target.total_children = self.shared_duplist.get_children_count(target.path)
                self.duplicates = self.shared_duplist.find_children(target.path)

                if target.status == "pending" and target.total_children == 0:
                    target.status = "finished"
                    self.cur_target = None
                    self.duplicates = None
                    self.shared_duplist = None
                    continue

                if target.storage.parallelizable:
                    n = self.n_workers
                else:
                    n = 1

                self.start_workers(n, DuplicateRemoverWorker, self)
                self.join_workers()

                self.shared_duplist.commit()

                if target.status == "pending":
                    if target.progress["finished"] == target.total_children:
                        target.status = "finished"
                    elif target.progress["suspended"] > 0:
                        target.status = "suspended"
                    elif target.progress["failed"] > 0:
                        target.status = "failed"

                self.cur_target = None
                self.duplicates = None
                self.shared_duplist = None
            except Exception as e:
                if self.shared_duplist is not None:
                    self.shared_duplist.commit()

                self.emit_event("error", e)
                if self.cur_target is not None:
                    self.cur_target.status = "failed"
