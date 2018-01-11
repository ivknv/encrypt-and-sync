#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from ..Task import Task
from ..Encryption import MIN_ENC_SIZE
from ..FileList import FileList
from .. import Paths
from .Worker import DownloaderWorker
from .Task import DownloadTask
from .Exceptions import NotFoundInDBError

__all__ = ["DownloadTarget"]

class DownloadTarget(Task):
    def __init__(self, downloader):
        Task.__init__(self)

        self.type = None
        self.downloader = downloader
        self.name = ""
        self.src = None
        self.dst = None
        self.src_path = ""
        self.dst_path = ""
        self.size = 0
        self.downloaded = 0

        self.tasks = []
        self.task_lock = threading.Lock()

    def stop_condition(self):
        if self.stopped or self.downloader.stopped:
            return True

        return self.status not in (None, "pending")

    def get_next_task(self):
        with self.task_lock:
            try:
                return self.tasks.pop(0)
            except IndexError:
                pass

    def get_tasks(self):
        flist = FileList(self.name, self.src.storage.name, self.downloader.directory)
        flist.create()

        nodes = flist.find_node_children(self.src_path)

        try:
            node = next(nodes)
        except StopIteration:
            # Fail if not found
            msg = "Path wasn't found in the database: %r" % (self.src_path,)
            raise NotFoundInDBError(msg, self.src_path)

        self.type = node["type"]
        self.total_children = 0

        try:
            dst_type = self.dst.get_meta(self.dst_path)["type"]
        except FileNotFoundError:
            dst_type = None

        if self.type == "f":
            new_task = DownloadTask(self)
            new_task.type = "f"
            new_task.modified = node["modified"]
            new_task.src = self.src
            new_task.dst = self.dst
            new_task.src_path = node["path"]
            new_task.dst_path = self.dst_path

            if self.src.is_encrypted(new_task.src_path):
                new_task.download_size = node["padded_size"] + MIN_ENC_SIZE

            if self.dst.is_encrypted(new_task.dst_path):
                new_task.upload_size = node["padded_size"] + MIN_ENC_SIZE

            if dst_type == "d":
                filename = Paths.split(new_task.src_path)[1]
                new_task.dst_path = Paths.join(new_task.dst_path, filename)

            self.total_children += 1

            yield new_task
            return

        for node in nodes:
            if self.stop_condition():
                return

            new_task = DownloadTask(self)

            new_task.type = node["type"]
            new_task.modified = node["modified"]
            new_task.src = self.src
            new_task.dst = self.dst
            new_task.src_path = node["path"]
            new_task.dst_path = self.dst_path

            # Set destination path
            if dst_type == "d" or self.type == "d":
                suffix = Paths.cut_prefix(node["path"], self.src_path)
                new_task.dst_path = Paths.join(new_task.dst_path, suffix)

            if new_task.type == "f" and self.src.is_encrypted(new_task.src_path):
                new_task.download_size = node["padded_size"] + MIN_ENC_SIZE
                
            if new_task.type == "f" and self.dst.is_encrypted(new_task.dst_path):
                new_task.upload_size = node["padded_size"] + MIN_ENC_SIZE

            self.total_children += 1

            yield new_task

    def complete(self, worker):
        if self.total_children == 0:
            with self.task_lock:
                self.tasks.clear()
                self.tasks.extend(self.get_tasks())

        if self.stop_condition():
            return True

        self.status = "pending"

        self.downloader.start_workers(self.downloader.n_workers,
                                      DownloaderWorker, self.downloader)
        self.downloader.join_workers()

        self.status = "finished"

        return True
