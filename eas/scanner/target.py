# -*- coding: utf-8 -*-

import threading

from ..task import Task
from ..filelist import FileList, DuplicateList
from ..scannable import DecryptedScannable, EncryptedScannable
from ..worker import WorkerPool, get_current_worker
from .. import path_match
from .. import Paths
from .tasks import EncryptedScanTask, DecryptedScanTask
from .tasks import AsyncEncryptedScanTask, AsyncDecryptedScanTask
from .worker import ScanWorker

__all__ = ["ScanTarget"]

class ScanTarget(Task):
    """
        Events: next_node, duplicates_found, scan_finished
    """

    def __init__(self, scanner, name):
        self._stopped = True

        Task.__init__(self)

        self.scanner = scanner
        self.config = scanner.config
        self.type = None
        self.name = name
        self.storage = None
        self.encrypted = False

        self.path = ""
        self.filename_encoding = "base64"

        self.shared_flist = FileList(name, scanner.directory)
        self.shared_duplist = None

        try:
            folder = self.config.folders[name]
        except KeyError:
            raise ValueError("Unknown folder: %r" % (name,))

        self.type = folder["type"]
        self.encrypted = folder["encrypted"]
        self.path = folder["path"]
        self.filename_encoding = folder["filename_encoding"]

        self.n_workers = 1

        self.pool = WorkerPool(None)

    @property
    def stopped(self):
        if self._stopped or self.scanner.stopped:
            return True

        return self.status not in (None, "pending")

    @stopped.setter
    def stopped(self, value):
        self._stopped = value

    def begin_scan(self):
        self.shared_flist.clear()

        if self.encrypted:
            self.shared_duplist.remove_children(self.path)

        if self.stopped:
            return

        if self.encrypted:
            scannable = EncryptedScannable(self.storage, self.path,
                                           filename_encoding=self.filename_encoding)
        else:
            scannable = DecryptedScannable(self.storage, self.path)

        try:
            scannable.identify()
        except FileNotFoundError:
            return

        if self.stopped:
            return

        path = self.path

        if scannable.type == "d":
            path = Paths.dir_normalize(path)

        allowed_paths = self.config.allowed_paths.get(self.storage.name, [])

        if not path_match.match(path, allowed_paths):
            return

        if scannable.type is not None:
            self.shared_flist.insert_node(scannable.to_node())

            if self.storage.parallelizable:
                if self.encrypted:
                    task = AsyncEncryptedScanTask(self, scannable)
                else:
                    task = AsyncDecryptedScanTask(self, scannable)
            elif self.encrypted:
                task = EncryptedScanTask(self, scannable)
            else:
                task = DecryptedScanTask(self, scannable)

            self.pool.add_task(task)

    def complete(self):
        if self.stopped:
            return True

        worker = get_current_worker()

        self.storage = self.config.storages[self.type]
        self.shared_duplist = DuplicateList(self.storage.name, self.scanner.directory)

        if not self.scanner.enable_journal:
            self.shared_flist.disable_journal()
            self.shared_duplist.disable_journal()

        self.shared_flist.create()
        self.shared_duplist.create()

        self.status = "pending"

        try:
            self.shared_flist.begin_transaction()
            self.shared_duplist.begin_transaction()

            self.begin_scan()

            if self.stopped:
                self.shared_flist.rollback()
                self.shared_duplist.rollback()
                return True

            self.pool.clear()

            if self.storage.parallelizable:
                self.pool.spawn_many(self.n_workers, ScanWorker, self.scanner)
            elif self.pool.queue is not None:
                self.pool.spawn(ScanWorker, self.scanner)

            self.pool.wait_idle()
            self.pool.stop()

            if self.stopped:
                self.pool.join()
                self.shared_flist.rollback()
                self.shared_duplist.rollback()
                return True

            self.pool.join()

            self.pool.queue = None

            if self.status == "pending":
                self.shared_flist.commit()
                self.shared_duplist.commit()
                self.status = "finished" 

                self.emit_event("scan_finished")
            else:
                self.shared_flist.rollback()
                self.shared_duplist.rollback()
        except Exception as e:
            self.pool.stop()
            self.pool.queue = None
            self.shared_flist.rollback()
            self.shared_duplist.rollback()

            self.status = "failed"

            raise e

        return True
