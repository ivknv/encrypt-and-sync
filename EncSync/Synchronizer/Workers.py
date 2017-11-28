#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import os

from yadisk.exceptions import DiskNotFoundError
from yadisk.settings import DEFAULT_TIMEOUT, DEFAULT_UPLOAD_TIMEOUT

from .Logging import logger
from .SyncFile import SyncFile, SyncFileInterrupt
from .Exceptions import TooLongFilenameError
from ..Encryption import pad_size
from ..Worker import Worker
from ..LogReceiver import LogReceiver
from .. import Paths

COMMIT_INTERVAL = 7.5 * 60 # Seconds

def check_filename_length(path):
    return len(Paths.split(path)[1]) < 160

class SynchronizerWorker(Worker):
    def __init__(self, dispatcher):
        Worker.__init__(self, dispatcher)

        self.encsync = dispatcher.encsync
        self.speed_limit = dispatcher.speed_limit
        self.cur_task = None

        self.path = None

        self.llist = dispatcher.shared_llist
        self.rlist = dispatcher.shared_rlist
        self.duplist = dispatcher.shared_duplist

        self.add_event("next_task")
        self.add_event("autocommit")
        self.add_event("autocommit_failed")
        self.add_event("autocommit_finished")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def autocommit(self):
        self.emit_event("autocommit")

        try:
            if self.llist.time_since_last_commit() >= COMMIT_INTERVAL:
                self.llist.seamless_commit()

            if self.rlist.time_since_last_commit() >= COMMIT_INTERVAL:
                self.rlist.seamless_commit()
        except BaseException as e:
            self.emit_event("autocommit_failed")
            raise e

        self.emit_event("autocommit_finished")

    def work_func(self):
        raise NotImplementedError

    def get_IVs(self):
        remote_path = self.path.remote
        remote_prefix = self.path.remote_prefix
        path = self.path.path

        node = self.rlist.find_node(remote_path)
        if node["path"] is None:
            # Get parent IVs
            if path != "/":
                p = Paths.split(remote_path)[0]
            else:
                p = remote_prefix

            p = Paths.dir_normalize(p)

            node = self.rlist.find_node(p)

        return node["IVs"]

    def stop_condition(self):
        return self.parent.cur_target.status == "suspended" or self.stopped

    def work(self):
        while not self.stopped:
            try:
                if self.stop_condition():
                    break

                task = self.parent.get_next_task()
                self.cur_task = task

                if task is not None:
                    self.emit_event("next_task", task)

                if task is None or self.stop_condition():
                    self.stop()

                    if task is not None:
                        task.emit_event("interrupted")

                    break

                if task.status is None:
                    task.change_status("pending")

                self.path = task.path

                local_path = self.path.local

                if not check_filename_length(local_path):
                    raise TooLongFilenameError("Filename is too long: %r" % local_path, local_path)

                IVs = self.get_IVs()

                if IVs is not None:
                    self.path.IVs = IVs

                self.work_func()

                self.cur_task = None
            except BaseException as e:
                self.emit_event("error", e)
                if self.cur_task is not None:
                    self.cur_task.change_status("failed")

class UploadWorker(SynchronizerWorker):
    def get_info(self):
        if self.cur_task is not None:
            try:
                progress = float(self.cur_task.uploaded) / self.cur_task.size
            except ZeroDivisionError:
                progress = 1.0

            return {"operation": "uploading file",
                    "path": self.cur_task.path.path,
                    "progress": progress}

        return {"operation": "uploading file"}

    def work_func(self):
        remote_path = self.path.remote
        remote_path_enc = self.path.remote_enc
        local_path = self.path.local
        IVs = self.path.IVs

        task = self.cur_task

        try:
            new_size = pad_size(os.path.getsize(local_path))
        except FileNotFoundError:
            self.llist.remove_node(local_path)
            self.autocommit()

            task.change_status("finished")
            return

        temp_file = SyncFile(self.encsync.temp_encrypt(local_path), self, task)

        if new_size >= 700 * 1024**2:
            timeout = (DEFAULT_TIMEOUT[0], 300.0)
        else:
            timeout = DEFAULT_UPLOAD_TIMEOUT

        if task.status == "pending":
            try:
                r = self.encsync.ynd.upload(temp_file,
                                            remote_path_enc,
                                            overwrite=True,
                                            timeout=timeout)
            except SyncFileInterrupt:
                return

        self.llist.update_size(local_path, new_size)

        if task.status != "pending":
            return

        newnode = {"type":        "f",
                   "path":        remote_path,
                   "padded_size": new_size,
                   "modified":    time.mktime(time.gmtime()),
                   "IVs":         IVs}

        self.rlist.insert_node(newnode)
        self.autocommit()

        task.change_status("finished")

class MkdirWorker(SynchronizerWorker):
    def get_info(self):
        if self.path is not None:
            return {"operation": "creating directory",
                    "path": self.path.path}
        else:
            return {"operation": "creating directory"}

    def work_func(self):
        remote_path = self.path.remote
        remote_path_enc = self.path.remote_enc
        local_path = self.path.local
        IVs = self.path.IVs

        task = self.cur_task

        if not os.path.exists(local_path):
            self.llist.remove_node(local_path)
            self.autocommit()

            task.change_status("finished")
            return

        r = self.encsync.ynd.mkdir(remote_path_enc)

        newnode = {"type": "d",
                   "path": remote_path,
                   "modified": time.mktime(time.gmtime()),
                   "padded_size": 0,
                   "IVs": IVs}

        self.rlist.insert_node(newnode)
        self.autocommit()

        task.change_status("finished")

class RmWorker(SynchronizerWorker):
    def get_info(self):
        if self.path is not None:
            return {"operation": "removing",
                    "path": self.path.path}
        else:
            return {"operation": "removing"}

    def work_func(self):
        remote_path = self.path.remote
        remote_path_enc = self.path.remote_enc
        local_path = self.path.local

        task = self.cur_task

        try:
            r = self.encsync.ynd.remove(remote_path_enc)
        except DiskNotFoundError:
            pass

        self.rlist.remove_node_children(remote_path)
        self.rlist.remove_node(remote_path)
        self.autocommit()

        task.change_status("finished")

class RmDupWorker(SynchronizerWorker):
    def get_info(self):
        if self.path is not None:
            return {"operation": "removing duplicate",
                    "path": self.path.path}
        else:
            return {"operation": "removing duplicate"}

    def get_IVs(self):
        return self.cur_task.path.IVs

    def work_func(self):
        remote_path = self.path.remote
        remote_path_enc = self.path.remote_enc

        task = self.cur_task

        try:
            r = self.encsync.ynd.remove(remote_path_enc)
        except DiskNotFoundError:
            pass

        self.duplist.remove(self.path.IVs, remote_path)
        self.autocommit()
        task.change_status("finished")
