#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Logging import logger
from ..Encryption import pad_size, MIN_ENC_SIZE
from ..Worker import Worker
from ..FileList import FileList
from ..LogReceiver import LogReceiver
from ..Storage.Exceptions import ControllerInterrupt
from .. import Paths

def check_if_download(task):
    try:
        meta = task.dst.get_meta(task.dst_path)
    except FileNotFoundError:
        return True

    if not meta["type"]:
        return True

    size1 = meta["size"] or 0
    modified1 = meta["modified"] or 0

    size2 = task.size
    modified2 = task.modified

    if task.src.encrypted:
        if not task.dst.is_encrypted(task.dst_path):
            size2 = max(size2 - MIN_ENC_SIZE, 0)
            size1 = pad_size(size1)
    elif task.dst.is_encrypted(task.dst_path):
        size1 = max(size1 - MIN_ENC_SIZE, 0)
        size2 = pad_size(size2)

    return size1 != size2 or modified1 < modified2

def recursive_mkdir(path, dst):
    path = Paths.join_properly("/", path)

    p = "/"

    for i in path.split("/"):
        if not i:
            continue

        p = Paths.join(p, i)

        try:
            dst.mkdir(p)
        except (FileExistsError, PermissionError):
            pass

class DownloaderWorker(Worker):
    def __init__(self, dispatcher, target):
        Worker.__init__(self, dispatcher)
        self.target = target
        self.pool = self.target.pool
        self.encsync = dispatcher.encsync
        self.lock = self.target.pool_lock
        self.speed_limit = dispatcher.speed_limit
        self.cur_task = None

        self.download_controller = None
        self.upload_controller = None

        self.add_event("next_task")
        self.add_event("error")

        callback1 = lambda e, x: setattr(self.cur_task, "downloaded", x)
        callback2 = lambda e, x: setattr(self.cur_task, "uploaded", x)
        self.add_callback("downloaded_changed", callback1)
        self.add_callback("uploaded_changed", callback2)

        self.add_receiver(LogReceiver(logger))

    def stop_condition(self):
        return self.stopped or self.parent.cur_target.status == "suspended"

    def stop(self):
        Worker.stop(self)

        if self.download_controller is not None:
            self.download_controller.stop()

        if self.upload_controller is not None:
            self.upload_controller.stop()

    def get_info(self):
        if self.cur_task is not None:
            try:
                progress = float(self.cur_task.downloaded) / self.cur_task.size
            except ZeroDivisionError:
                progress = 1.0

            return {"operation": "downloading",
                    "path":      self.cur_task.src_path,
                    "progress":  progress}

        return {"operation": "downloading",
                "progress":  0.0}

    def get_file_size(self, task):
        if task.src.encrypted:
            flist = FileList(self.target.name,
                             self.target.src.storage.name,
                             self.parent.directory)

            node = flist.find_node(Paths.join(self.target.src.prefix, task.src_path))
            if node["padded_size"]:
                return node["padded_size"] + MIN_ENC_SIZE

            return task.size
        else:
            return task.src.get_meta(task.src_path)["size"] or 0

    def download_file(self, task):
        try:
            if task.dst.is_dir(task.dst_path):
                name = Paths.split(task.src_path)[1]
                task.dst_path = Paths.join(task.dst_path, name)

            if self.stop_condition():
                return

            if not task.src.encrypted:
                # In this case the size was not determined yet
                try:
                    task.size = self.get_file_size(task)
                except FileNotFoundError:
                    task.change_status("failed")
                    return

            if not check_if_download(task):
                task.change_status("finished")
                return

            if self.stop_condition():
                return

            recursive_mkdir(Paths.split(task.dst_path)[0], task.dst)

            if self.stop_condition():
                return

            if task.dst.is_encrypted(task.dst_path):
                download_generator = task.src.get_encrypted_file(task.src_path)
            else:
                download_generator = task.src.get_file(task.src_path)

            self.download_controller = next(download_generator)
            if self.download_controller is not None:
                self.download_controller.add_receiver(self)

            if self.stop_condition():
                return

            try:
                tmpfile = next(download_generator)

                self.upload_controller, ivs = task.dst.upload(tmpfile, task.dst_path)

                if self.stop_condition():
                    return

                self.upload_controller.add_receiver(self)
                self.upload_controller.work()
            except ControllerInterrupt:
                return

            task.change_status("finished")
        except BaseException as e:
            self.emit_event("error", e)
            task.change_status("failed")

    def work(self):
        while not self.stopped:
            try:
                with self.lock:
                    if self.stopped or not len(self.pool):
                        break

                    task = self.pool.pop(0)
                    self.cur_task = task

                    self.emit_event("next_task", task)

                    if task.parent is not None and task.parent.status == "suspended":
                        continue

                    if task.status is None:
                        task.change_status("pending")
                    elif task.status != "pending":
                        continue

                if task.type == "d":
                    recursive_mkdir(task.dst_path, task.dst)
                    task.change_status("finished")
                else:
                    self.download_file(task)

                self.cur_task = None
                self.upload_controller = None
                self.download_controller = None
            except BaseException as e:
                self.emit_event("error", e)

                if self.cur_task is not None:
                    self.cur_task.change_status("failed")
