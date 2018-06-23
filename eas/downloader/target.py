# -*- coding: utf-8 -*-

from ..task import Task
from ..encryption import MIN_ENC_SIZE
from ..filelist import Filelist
from ..scannable import EncryptedScannable, DecryptedScannable, scan_files
from ..encrypted_storage import EncryptedStorage
from ..worker import WorkerPool
from ..common import threadsafe_iterator
from .. import pathm
from .worker import DownloaderWorker
from .task import DownloadTask

__all__ = ["DownloadTarget"]

class DownloadTarget(Task):
    def __init__(self, downloader, src_storage_name, src_path, dst_storage_name, dst_path):
        Task.__init__(self)

        self.src_storage_name = src_storage_name
        self.dst_storage_name = dst_storage_name
        self.src_path = src_path
        self.dst_path = dst_path

        self.type = None
        self.downloader = downloader
        self.config = downloader.config
        self.src = None
        self.dst = None
        self.size = 0
        self.downloaded = 0

        self.upload_limit = downloader.upload_limit
        self.download_limit = downloader.download_limit

        self.skip_downloaded = True

        self.n_workers = 1

        self.pool = WorkerPool(None)

    def stop(self):
        super().stop()

        self.pool.stop()

    def node_to_task(self, node, dst_type):
        new_task = DownloadTask(self)

        new_task.type = node["type"]
        new_task.IVs = node["IVs"]
        new_task.modified = node["modified"]
        new_task.src = self.src
        new_task.dst = self.dst
        new_task.src_path = node["path"]
        new_task.dst_path = self.dst_path

        assert(self.type in ("f", "d"))

        if self.type == "f" and dst_type == "d":
            filename = pathm.split(new_task.src_path)[1]
            new_task.dst_path = pathm.join(new_task.dst_path, filename)
        elif dst_type == "d" or self.type == "d":
            suffix = pathm.cut_prefix(node["path"], self.src_path)
            new_task.dst_path = pathm.join(new_task.dst_path, suffix)

        if new_task.type == "f" and self.src.is_encrypted(new_task.src_path):
            new_task.download_size = node["padded_size"] + MIN_ENC_SIZE
            
        if new_task.type == "f" and self.dst.is_encrypted(new_task.dst_path):
            new_task.upload_size = node["padded_size"] + MIN_ENC_SIZE

        new_task.upload_limit = self.upload_limit
        new_task.download_limit = self.download_limit

        return new_task

    @threadsafe_iterator
    def task_iterator(self, nodes):
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
            scannable = DecryptedScannable(self.src.storage, path=self.src_path)
            scannable.identify()

            self.type = scannable.type

            nodes = (i[1] for i in scan_files(scannable))
            nodes = (j for i in ([scannable.to_node()], nodes) for j in i)
        else:
            folder_name = folder["name"]
            flist = Filelist(folder_name, self.downloader.directory)
            flist.create()

            root_node = flist.find(self.src_path)

            if root_node["type"] is not None:
                self.type = root_node["type"]
                self.expected_total_children = flist.get_file_count(self.src_path)

                nodes = flist.find_recursively(self.src_path)
            else:
                self.expected_total_children = -1

                if self.src.is_encrypted(self.src_path):
                    folder_storage = self.src.get_folder_storage(folder_name)

                    prefix = folder["path"]
                    enc_path = folder_storage.encrypt_path(self.src_path)[0]
                    filename_encoding = folder_storage.filename_encoding

                    scannable = EncryptedScannable(self.src.storage, prefix,
                                                   enc_path=enc_path,
                                                   filename_encoding=filename_encoding)
                else:
                    scannable = DecryptedScannable(self.src.storage, path=self.src_path)

                scannable.identify()

                self.type = scannable.type

                nodes = (i[1] for i in scan_files(scannable))
                nodes = (j for i in ([scannable.to_node()], nodes) for j in i)

        self.pool.queue = self.task_iterator(nodes)

    def complete(self):
        self.src = EncryptedStorage(self.config, self.src_storage_name, self.downloader.directory)
        self.dst = EncryptedStorage(self.config, self.dst_storage_name, self.downloader.directory)

        if self.total_children == 0:
            self.set_tasks()
            
        if self.stopped:
            return True

        self.status = "pending"

        if self.src.storage.parallelizable or self.dst.storage.parallelizable:
            n_workers = self.n_workers
        else:
            n_workers = 1

        self.pool.clear()

        self.pool.spawn_many(n_workers, DownloaderWorker, self.downloader)
        self.pool.join()

        if self.stopped:
            return True

        if self.status in (None, "pending"):
            self.status = "finished"

        return True
