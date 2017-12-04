#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading

from .Logging import logger
from .Worker import DownloaderWorker
from .DownloadTask import DownloadTask
from .DownloadTarget import DownloadTarget
from .Exceptions import NotFoundInDBError
from ..Encryption import MIN_ENC_SIZE
from ..FileList import RemoteFileList
from ..Worker import Worker
from ..LogReceiver import LogReceiver
from .. import Paths

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
                i.change_status(status)

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def make_target(self, name, remote, local):
        try:
            encsync_target = self.encsync.targets[name]
        except KeyError:
            raise ValueError("Unknown target: %r" % (name,))

        target = DownloadTarget(name)
        target.local = Paths.to_sys(local)
        target.remote = remote
        target.prefix = encsync_target["remote"]
        target.filename_encoding = encsync_target["filename_encoding"]

    def add_download(self, name, remote, local):
        target = self.make_target(name, remote, local)

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
                    if self.stopped or not len(self.targets):
                        break
                    target = self.targets.pop(0)
                    self.cur_target = target

                self.emit_event("next_target", target)

                if target.status == "suspended":
                    continue

                target.change_status("pending")

                if target.total_children == 0:
                    self.scan(target)

                with target.pool_lock, target.lock:
                    for i in target.children:
                        if i.status in {"pending", None}:
                            target.pool.append(i)

                if self.stopped:
                    break

                self.init_workers()
                self.join_workers()

                self.cur_target = None
            except BaseException as e:
                self.emit_event("error", e)
                if self.cur_target is not None:
                    self.cur_target.change_status("failed")

    def init_workers(self):
        n_running = sum(1 for i in self.get_worker_list() if i.is_alive())

        self.start_workers(self.n_workers - n_running,
                           DownloaderWorker, self, self.cur_target)

    def scan(self, target):
        rlist = RemoteFileList(target.name, self.directory)

        rlist.create()

        dec_remote = target.remote

        nodes = list(rlist.find_node_children(dec_remote))

        if len(nodes) == 0:
            # Fail if not found
            raise NotFoundInDBError("Path wasn't found in the database: %r" % dec_remote, dec_remote)

        target.type = nodes[0]["type"]
        target.total_children = 0

        for node in nodes:
            new_task = DownloadTask()

            enc_path = self.encsync.encrypt_path(node["path"], target.prefix, node["IVs"],
                                                 filename_encoding=target.filename_encoding)[0]
            name = Paths.cut_prefix(node["path"], target.remote)

            new_task.type = node["type"]
            new_task.modified = node["modified"]
            new_task.remote = enc_path
            new_task.dec_remote = node["path"]

            # Set destination path
            if os.path.isdir(target.local) or target.type == "d":
                new_task.local = os.path.join(target.local, name)
            elif target.type == "f":
                new_task.local = target.local

            new_task.parent = target
            new_task.IVs = node["IVs"]

            if new_task.type == "f":
                new_task.size = node["padded_size"] + MIN_ENC_SIZE
            else:
                new_task.size = 0

            with target.lock:
                target.total_children += 1
                target.size += new_task.size
                target.children.append(new_task)
