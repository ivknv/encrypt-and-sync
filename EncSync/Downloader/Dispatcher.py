#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from ..Encryption import MIN_ENC_SIZE
from .. import SyncList
from .. import paths
from ..Dispatcher import Dispatcher
from .Logging import logger
from .Worker import DownloaderWorker
from .DownloadTask import DownloadTask

class DownloaderDispatcher(Dispatcher):
    def __init__(self, downloader):
        Dispatcher.__init__(self)

        self.downloader = downloader
        self.encsync = downloader.encsync
        self.n_workers = downloader.n_workers
        self.speed_limit = downloader.speed_limit
        self.cur_target = None

    def set_speed_limit(self, limit):
        self.speed_limit = limit

        for worker in self.get_worker_list():
            worker.speed_limit = self.speed_limit

    def work(self):
        while not self.stopped:
            with self.downloader.targets_lock:
                if self.stopped or not len(self.downloader.targets):
                    break
                target = self.downloader.targets.pop(0)
                self.cur_target = target

            if target.status == "suspended":
                continue

            target.change_status("pending")

            logger.debug("Scanning download target")

            if target.total_children == 0:
                if target.type == "f":
                    new_target = DownloadTask()

                    synclist = SyncList.SyncList()

                    node = synclist.find_remote_node(target.dec_remote)

                    if node["padded_size"] is None:
                        target.change_status("failed")
                        continue

                    new_target.type = "f"
                    new_target.remote = target.remote
                    new_target.dec_remote = target.dec_remote
                    new_target.local = target.local
                    new_target.parent = target
                    new_target.IVs = target.IVs
                    new_target.size = node["padded_size"]

                    with target.lock:
                        target.total_children += 1
                        target.size = new_target.size
                        target.children.append(new_target)
                else:
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
        synclist = SyncList.SyncList()
        with synclist:
            synclist.create()
            synclist.commit()

        dec_remote = target.dec_remote

        nodes = list(synclist.find_remote_node_children(dec_remote))

        if len(nodes) == 0:
            # Fail if not found
            logger.debug("Target path ({}) wasn't found in the database".format(dec_remote))
            target.change_status("failed")
            return

        if nodes[0]["type"] == "f":
            return

        with target.lock:
            target.total_children = 0

        for node in nodes:
            new_target = DownloadTask()

            enc_path = self.encsync.encrypt_path(node["path"], target.prefix, node["IVs"])[0]
            enc_name = paths.cut_prefix(enc_path, target.remote)
            name = self.encsync.decrypt_path(enc_name)[0]

            new_target.type = node["type"]
            new_target.remote = enc_path
            new_target.dec_remote = node["path"]
            new_target.local = os.path.join(target.local, name)
            new_target.parent = target
            new_target.IVs = node["IVs"]

            if new_target.type == "f":
                new_target.size = node["padded_size"] + MIN_ENC_SIZE
            else:
                new_target.size = 0

            with target.lock:
                target.total_children += 1
                target.size += new_target.size
                target.children.append(new_target)
