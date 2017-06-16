#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading

from ..Encryption import MIN_ENC_SIZE
from ..FileList import RemoteFileList
from .. import Paths
from ..Worker import Worker
from .Logging import logger
from .Worker import DownloaderWorker
from .DownloadTask import DownloadTask
from .DownloadTarget import DownloadTarget

class Downloader(Worker):
    def __init__(self, encsync, directory, n_workers=2):
        Worker.__init__(self)

        self.encsync = encsync
        self.targets = []
        self.n_workers = n_workers
        self.directory = directory

        self.targets_lock = threading.Lock()
        self.speed_limit = 1024**4 / n_workers # Bytes per second

        self.cur_target = None

        self.add_event("next_target")
        self.add_event("next_task")

    def change_status(self, status):
        for i in self.get_targets():
            i.change_status(status)

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def add_download(self, remote_prefix, remote, local):
        target = DownloadTarget()
        target.local = Paths.to_sys(local)
        target.remote = remote
        target.prefix = remote_prefix

        self.add_target(target)

        return target

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

        return target

    def set_speed_limit(self, limit):
        self.speed_limit = limit / self.n_workers

        for worker in self.get_worker_list():
            worker.speed_limit = self.speed_limit

    def work(self):
        while not self.stopped:
            with self.targets_lock:
                if self.stopped or not len(self.targets):
                    break
                target = self.targets.pop(0)
                self.cur_target = target

            self.emit_event("next_target", target)

            if target.status == "suspended":
                continue

            target.change_status("pending")

            logger.debug("Scanning download target")

            if target.total_children == 0:
                self.scan(target)

            logger.debug("Done scanning download target")

            with target.pool_lock, target.lock:
                for i in target.children:
                    if i.status in {"pending", None}:
                        target.pool.append(i)

            if self.stopped:
                break

            self.init_workers()
            self.join_workers()

        logger.debug("No more targets to download")

    def init_workers(self):
        logger.debug("Starting workers")

        n_running = sum(1 for i in self.get_worker_list() if i.is_alive())

        self.start_workers(self.n_workers - n_running,
                           DownloaderWorker, self, self.cur_target)

        logger.debug("Done starting workers")

    def scan(self, target):
        rlist = RemoteFileList(self.directory)

        rlist.create()

        dec_remote = target.remote

        nodes = list(rlist.find_node_children(dec_remote))

        if len(nodes) == 0:
            # Fail if not found
            logger.debug("Target path ({}) wasn't found in the database".format(dec_remote))
            target.emit_event("not_found_in_db")
            target.change_status("failed")
            return

        target.type = nodes[0]["type"]

        with target.lock:
            target.total_children = 0

        for node in nodes:
            new_task = DownloadTask()

            enc_path = self.encsync.encrypt_path(node["path"], target.prefix, node["IVs"])[0]
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
