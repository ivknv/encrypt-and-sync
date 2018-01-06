#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Logging import logger
from .Worker import DownloaderWorker
from .DownloadTask import DownloadTask
from .DownloadTarget import DownloadTarget
from .Exceptions import NotFoundInDBError
from ..Encryption import MIN_ENC_SIZE
from ..FileList import FileList
from ..Worker import Worker
from ..LogReceiver import LogReceiver
from ..EncryptedStorage import EncryptedStorage
from .. import Paths

__all__ = ["Downloader"]

class Downloader(Worker):
    def __init__(self, encsync, directory, n_workers=2):
        Worker.__init__(self)

        self.encsync = encsync
        self.targets = []
        self.n_workers = n_workers
        self.directory = directory

        self.targets_lock = threading.Lock()
        self.speed_limit = float("inf") # Bytes per second

        self.cur_target = None

        self.add_event("next_target")
        self.add_event("next_task")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def change_status(self, status):
        for i in self.get_targets() + [self.cur_target]:
            if i is not None:
                i.status = status

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def make_target(self, src_storage_name, src_path, dst_storage_name, dst_path):
        encsync_target, dir_type = self.encsync.identify_target(src_storage_name,
                                                                src_path)

        if encsync_target is None:
            raise ValueError("%r doesn't belong to any targets" % (src_path,))

        src = EncryptedStorage(self.encsync, src_storage_name, self.directory)
        dst = EncryptedStorage(self.encsync, dst_storage_name, self.directory)

        target = DownloadTarget()
        target.name = encsync_target["name"]
        target.src = src
        target.dst = dst
        target.src_path = src_path
        target.dst_path = dst_path

        return target

    def add_download(self, name, src_path, dst_storage_name, dst_path):
        target = self.make_target(name, src_path, dst_storage_name, dst_path)

        self.add_target(target)

        return target

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

        return target

    def set_speed_limit(self, limit):
        self.speed_limit = limit / float(self.n_workers)

        for worker in self.get_worker_list():
            worker.speed_limit = self.speed_limit

    def work(self):
        while not self.stopped:
            try:
                with self.targets_lock:
                    if self.stopped or not self.targets:
                        break

                    target = self.targets.pop(0)
                    self.cur_target = target

                self.emit_event("next_target", target)

                if target.status == "suspended":
                    continue

                target.status = "pending"

                if target.total_children == 0:
                    self.scan(target)

                with target.pool_lock, target.lock:
                    for i in target.children:
                        if i.status in ("pending", None):
                            target.pool.append(i)

                if self.stopped or target.status != "pending":
                    break

                self.init_workers()
                self.join_workers()

                self.cur_target = None
            except Exception as e:
                self.emit_event("error", e)
                if self.cur_target is not None:
                    self.cur_target.status = "failed"

    def init_workers(self):
        n_running = sum(1 for i in self.get_worker_list() if i.is_alive())
        
        self.start_workers(self.n_workers - n_running,
                           DownloaderWorker, self, self.cur_target)

    def scan(self, target):
        flist = FileList(target.name, target.src.storage.name, self.directory)
        flist.create()

        src_path = target.src_path

        nodes = flist.find_node_children(src_path)

        try:
            node = next(nodes)
        except StopIteration:
            # Fail if not found
            msg = "Path wasn't found in the database: %r" % (src_path,)
            raise NotFoundInDBError(msg, src_path)

        target.type = node["type"]
        target.total_children = 0

        try:
            dst_type = target.dst.get_meta(target.dst_path)["type"]
        except FileNotFoundError:
            dst_type = None

        if target.type == "f":
            new_task = DownloadTask()
            new_task.type = "f"
            new_task.modified = node["modified"]
            new_task.src = target.src
            new_task.dst = target.dst
            new_task.src_path = node["path"]
            new_task.dst_path = target.dst_path
            new_task.parent = target

            if target.src.is_encrypted(new_task.src_path):
                new_task.download_size = node["padded_size"] + MIN_ENC_SIZE

            if target.dst.is_encrypted(new_task.dst_path):
                new_task.upload_size = node["padded_size"] + MIN_ENC_SIZE

            if dst_type == "d":
                filename = Paths.split(new_task.src_path)[1]
                new_task.dst_path = Paths.join(new_task.dst_path, filename)

            target.total_children = 1
            target.children.append(new_task)

            return

        for node in nodes:
            if self.stopped or target.status != "pending":
                return

            new_task = DownloadTask()

            new_task.type = node["type"]
            new_task.modified = node["modified"]
            new_task.src = target.src
            new_task.dst = target.dst
            new_task.src_path = node["path"]
            new_task.dst_path = target.dst_path

            # Set destination path
            if dst_type == "d" or target.type == "d":
                suffix = Paths.cut_prefix(node["path"], target.src_path)
                new_task.dst_path = Paths.join(new_task.dst_path, suffix)

            new_task.parent = target

            if new_task.type == "f" and target.src.is_encrypted(new_task.src_path):
                new_task.download_size = node["padded_size"] + MIN_ENC_SIZE
                
            if new_task.type == "f" and target.dst.is_encrypted(new_task.dst_path):
                new_task.upload_size = node["padded_size"] + MIN_ENC_SIZE

            target.total_children += 1
            target.children.append(new_task)
