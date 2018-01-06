#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from ..constants import DEFAULT_UPLOAD_TIMEOUT

from .Logging import logger
from ..Worker import Worker
from ..Encryption import pad_size
from ..LogReceiver import LogReceiver
from ..Storage.Exceptions import ControllerInterrupt
from ..common import get_file_size
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

        self.src = None
        self.dst = None

        self.path = None

        self.dst_path = None
        self.src_path = None

        self.flist1 = dispatcher.shared_flist1
        self.flist2 = dispatcher.shared_flist2

        self.add_event("next_task")
        self.add_event("autocommit_started")
        self.add_event("autocommit_failed")
        self.add_event("autocommit_finished")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def autocommit(self):
        try:
            if self.flist1.time_since_last_commit() >= COMMIT_INTERVAL:
                self.emit_event("autocommit_started", self.flist1)
                self.flist2.seamless_commit()
                self.emit_event("autocommit_finished", self.flist1)
        except Exception as e:
            self.emit_event("autocommit_failed", self.flist1)
            raise e

        try:
            if self.flist2.time_since_last_commit() >= COMMIT_INTERVAL:
                self.emit_event("autocommit_started", self.flist2)
                self.flist2.seamless_commit()
                self.emit_event("autocommit_finished", self.flist2)
        except Exception as e:
            self.emit_event("autocommit_failed", self.flist2)
            raise e

    def work_func(self):
        raise NotImplementedError

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
                    task.status = "pending"

                self.path = task.path
                self.src = self.parent.cur_target.src
                self.dst = self.parent.cur_target.dst
                self.src_path = Paths.join(self.src.prefix, self.path)
                self.dst_path = Paths.join(self.dst.prefix, self.path)

                self.work_func()

                self.cur_task = None
            except Exception as e:
                self.emit_event("error", e)
                if self.cur_task is not None:
                    self.cur_task.status = "failed"

class UploadWorker(SynchronizerWorker):
    def __init__(self, *args, **kwargs):
        SynchronizerWorker.__init__(self, *args, **kwargs)

        self.upload_controller = None
        self.download_controller = None

        callback1 = lambda e, x: setattr(self.cur_task, "uploaded", x)
        callback2 = lambda e, x: setattr(self.cur_task, "downloaded", x)
        self.add_callback("uploaded_changed", callback1)
        self.add_callback("downloaded_changed", callback2)

    def stop(self):
        SynchronizerWorker.stop(self)

        if self.upload_controller is not None:
            self.upload_controller.stop()

    def get_info(self):
        if self.cur_task is not None:
            try:
                progress = float(self.cur_task.uploaded) / self.cur_task.size
            except ZeroDivisionError:
                progress = 1.0

            return {"operation": "uploading file",
                    "path": self.path,
                    "progress": progress}

        return {"operation": "uploading file"}

    def work_func(self):
        task = self.cur_task

        try:
            meta = self.src.get_meta(self.path)
            new_size = pad_size(meta["size"])
        except FileNotFoundError:
            self.flist1.remove_node(self.src_path)
            self.autocommit()

            task.status = "finished"
            return

        timeout = DEFAULT_UPLOAD_TIMEOUT

        if new_size >= 700 * 1024**2:
            if not isinstance(timeout, (tuple, list)):
                connect_timeout = read_timeout = timeout
            else:
                connect_timeout, read_timeout = timeout

            new_read_timeout = 300.0

            if read_timeout < new_read_timeout:
                timeout = (connect_timeout, new_read_timeout)

        if self.dst.encrypted:
            download_generator = self.src.get_encrypted_file(self.path)
        else:
            download_generator = self.src.get_file(self.path)

        self.download_controller = next(download_generator)
        if self.download_controller is not None:
            self.download_controller.add_receiver(self)

        temp_file = next(download_generator)

        if task.status == "pending":
            task.size = get_file_size(temp_file)
            controller, ivs = self.dst.upload(temp_file, self.path, timeout=timeout)
            self.upload_controller = controller
            controller.add_receiver(self)

            if self.stop_condition():
                return

            try:
                controller.work()
            except ControllerInterrupt:
                return

        self.flist1.update_size(self.src_path, new_size)

        if task.status != "pending":
            return

        newnode = {"type":        "f",
                   "path":        self.dst_path,
                   "padded_size": new_size,
                   "modified":    time.mktime(time.gmtime()),
                   "IVs":         ivs}

        self.flist2.insert_node(newnode)
        self.autocommit()

        task.status = "finished"

class MkdirWorker(SynchronizerWorker):
    def get_info(self):
        if self.path is not None:
            return {"operation": "creating directory",
                    "path": self.path}
        else:
            return {"operation": "creating directory"}

    def work_func(self):
        task = self.cur_task

        if not self.src.exists(self.path):
            self.flist1.remove_node(self.src_path)
            self.autocommit()

            task.status = "finished"
            return

        ivs = self.dst.mkdir(self.path)

        newnode = {"type": "d",
                   "path": self.dst_path,
                   "modified": time.mktime(time.gmtime()),
                   "padded_size": 0,
                   "IVs": ivs}

        self.flist2.insert_node(newnode)
        self.autocommit()

        task.status = "finished"

class RmWorker(SynchronizerWorker):
    def get_info(self):
        if self.path is not None:
            return {"operation": "removing",
                    "path": self.path}
        else:
            return {"operation": "removing"}

    def work_func(self):
        task = self.cur_task

        try:
            self.dst.remove(self.path)
        except FileNotFoundError:
            pass

        self.flist2.remove_node_children(self.dst_path)
        self.flist2.remove_node(self.dst_path)
        self.autocommit()

        task.status = "finished"
