#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from ..Task import Task
from ..Encryption import MIN_ENC_SIZE
from ..FileList import FileList
from ..Scannable import EncryptedScannable, DecryptedScannable, scan_files
from ..EncryptedStorage import EncryptedStorage
from .. import Paths
from .Worker import DownloaderWorker
from .Task import DownloadTask

__all__ = ["DownloadTarget"]

class DownloadTarget(Task):
    def __init__(self, downloader, src_storage_name, dst_storage_name):
        Task.__init__(self)

        self.src_storage_name = src_storage_name
        self.dst_storage_name = dst_storage_name

        self.type = None
        self.downloader = downloader
        self.config = downloader.config
        self.src = None
        self.dst = None
        self.src_path = ""
        self.dst_path = ""
        self.size = 0
        self.downloaded = 0

        self.tasks = None
        self.task_lock = threading.Lock()

        self.upload_limit = downloader.upload_limit
        self.download_limit = downloader.download_limit

    def stop_condition(self):
        if self.stopped or self.downloader.stopped:
            return True

        return self.status not in (None, "pending")

    def get_next_task(self):
        with self.task_lock:
            try:
                return next(self.tasks)
            except StopIteration:
                pass

    def node_to_task(self, node, dst_type):
        new_task = DownloadTask(self)

        new_task.type = node["type"]
        new_task.modified = node["modified"]
        new_task.src = self.src
        new_task.dst = self.dst
        new_task.src_path = node["path"]
        new_task.dst_path = self.dst_path

        if self.type == "f" and dst_type == "d":
            filename = Paths.split(new_task.src_path)[1]
            new_task.dst_path = Paths.join(new_task.dst_path, filename)
        elif dst_type == "d" or self.type == "d":
            suffix = Paths.cut_prefix(node["path"], self.src_path)
            new_task.dst_path = Paths.join(new_task.dst_path, suffix)

        if new_task.type == "f" and self.src.is_encrypted(new_task.src_path):
            new_task.download_size = node["padded_size"] + MIN_ENC_SIZE
            
        if new_task.type == "f" and self.dst.is_encrypted(new_task.dst_path):
            new_task.upload_size = node["padded_size"] + MIN_ENC_SIZE

        new_task.upload_limit = self.upload_limit
        new_task.download_limit = self.download_limit

        return new_task

    def task_generator(self, nodes):
        try:
            dst_type = self.dst.get_meta(self.dst_path)["type"]
        except FileNotFoundError:
            dst_type = None

        for node in nodes:
            yield self.node_to_task(node, dst_type)

    def set_tasks(self):
        folder = self.config.identify_folder(self.src.storage.name,
                                             self.src_path)

        if folder is None:
            self.expected_total_children = -1
            scannable = DecryptedScannable(self.src.storage, self.src_path)
            scannable.identify()

            self.type = scannable.type

            nodes = (i[1] for i in scan_files(scannable))
            nodes = (j for i in ([scannable.to_node()], nodes) for j in i)
        else:
            folder_name = folder["name"]
            flist = FileList(folder_name, self.downloader.directory)
            flist.create()

            root_node = flist.find_node(self.src_path)

            if root_node["type"] is not None:
                self.type = root_node["type"]
                self.expected_total_children = flist.get_file_count(self.src_path)

                nodes = flist.find_node_children(self.src_path)
            else:
                self.expected_total_children = -1

                if self.src.is_encrypted(self.src_path):
                    folder_storage = self.src.get_folder_storage(folder_name)

                    prefix = folder["path"]
                    enc_path = folder_storage.encrypt_path(self.src_path)[0]
                    filename_encoding = folder_storage.filename_encoding

                    scannable = EncryptedScannable(self.src.storage,
                                                   prefix, enc_path,
                                                   filename_encoding=filename_encoding)
                else:
                    scannable = DecryptedScannable(self.src.storage, self.src_path)

                nodes = (i[1] for i in scan_files(scannable))
                nodes = (j for i in ([scannable.to_node()], nodes) for j in i)

        self.tasks = self.task_generator(nodes)

    def complete(self, worker):
        self.src = EncryptedStorage(self.config, self.src_storage_name, self.downloader.directory)
        self.dst = EncryptedStorage(self.config, self.dst_storage_name, self.downloader.directory)

        if self.total_children == 0:
            self.set_tasks()
            
        if self.stop_condition():
            return True

        self.status = "pending"

        self.downloader.start_workers(self.downloader.n_workers,
                                      DownloaderWorker, self.downloader)
        self.downloader.join_workers()

        if self.stop_condition():
            return True

        if self.status in (None, "pending"):
            self.status = "finished"

        return True
