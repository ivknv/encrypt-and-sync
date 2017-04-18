#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import os

from .Logging import logger
from .SyncFile import SyncFile, SyncFileInterrupt
from ..SyncList import pad_size
from .. import paths

from ..Worker import Worker

def check_filename_length(path):
    return len(paths.split(path)[1]) < 160

class SynchronizerWorker(Worker):
    def __init__(self, dispatcher):
        Worker.__init__(self, dispatcher)

        self.encsync = dispatcher.encsync
        self.speed_limit = dispatcher.speed_limit
        self.cur_task = None

        self.path = None

        self.synclist = dispatcher.shared_synclist

    def work_func(self):
        pass

    def get_IVs(self):
        remote_path = self.path.remote
        remote_prefix = self.path.remote_prefix
        path = self.path.path

        node = self.synclist.find_remote_node(remote_path)
        if node["path"] is None:
            # Get parent IVs
            if path != "/":
                p = paths.split(remote_path)[0]
            else:
                p = remote_prefix

            p = paths.dir_normalize(p)

            node = self.synclist.find_remote_node(p)

        return node["IVs"]

    def stop_condition(self):
        return self.parent.cur_target.status == "suspended" or self.stopped

    def work(self):
        logger.debug("SynchronizerWorker began working")

        while not self.stopped:
            if self.stop_condition():
                logger.debug("SynchronizerWorker stopped")
                break

            task = self.parent.get_next_task()
            self.cur_task = task

            if task is None or self.stop_condition():
                self.stop()
                logger.debug("SynchronizerWorker stopped")
                break

            self.path = task.diff[2]

            local_path = self.path.local

            if not check_filename_length(local_path):
                task.change_status("failed")
                logger.debug("Filename is too long (>= 160): {}".format(local_path))
                continue

            IVs = self.get_IVs()

            if IVs is not None:
                self.path.IVs = IVs

            self.work_func()

        logger.debug("SynchronizerWorker finished working")

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

        logger.debug("Uploading file to {}".format(remote_path))

        try:
            if not os.path.exists(local_path):
                self.synclist.remove_local_node(local_path)

                task.change_status("finished")
                return

            temp_file = SyncFile(self.encsync.temp_encrypt(local_path), self, task)

            if task.status == "pending":
                try:
                    r = self.encsync.ynd.upload(temp_file, remote_path_enc, overwrite=True)

                    if not r["success"]:
                        task.change_status("failed")
                        logger.debug("Upload task failed")
                except SyncFileInterrupt:
                    logger.debug("Upload was interrupted")

            if task.status != "pending" or self.stop_condition():
                return

            new_size = pad_size(os.path.getsize(local_path))

            newnode = {"type": "f",
                       "path": remote_path,
                       "padded_size": new_size,
                       "modified": time.mktime(time.gmtime()),
                       "IVs": IVs}

            with self.synclist:
                self.synclist.insert_remote_node(newnode)
                self.synclist.update_local_size(local_path, new_size)

            task.change_status("finished")
        except:
            task.change_status("failed")
            logger.exception("An error occured")

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

        logger.debug("Creating directory {}".format(remote_path))

        try:
            if not os.path.exists(local_path):
                self.synclist.remove_local_node(local_path)

                task.change_status("finished")
                return

            r = self.encsync.ynd.mkdir(remote_path_enc)

            logger.debug(remote_path)

            if not r["success"]:
                task.change_status("failed")
                logger.debug("Folder creation task failed")

            if task.status == "failed":
                return

            newnode = {"type": "d",
                       "path": remote_path,
                       "modified": time.mktime(time.gmtime()),
                       "padded_size": 0,
                       "IVs": IVs}

            self.synclist.insert_remote_node(newnode)

            task.change_status("finished")
        except:
            task.change_status("failed")
            logger.exception("An error occured")

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

        logger.debug("Removing {}".format(remote_path))

        try:
            r = self.encsync.ynd.rm(remote_path_enc)

            if r["success"]:
                with self.synclist:
                    self.synclist.remove_remote_node_children(remote_path)
                    self.synclist.remove_remote_node(remote_path)
                task.change_status("finished")
            else:
                task.change_status("failed")
                logger.debug("Remove task failed")
        except:
            task.change_status("failed")
            logger.exception("An error occured")
