#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Task import Task
from ..Event.Receiver import Receiver
from ..Encryption import pad_size, MIN_ENC_SIZE
from ..FileList import FileList
from ..common import get_file_size
from ..Storage.Exceptions import ControllerInterrupt
from .. import Paths

__all__ = ["DownloadTask"]

class UploadControllerReceiver(Receiver):
    def __init__(self, task):
        Receiver.__init__(self)

        self.task = task

        self.add_callback("uploaded_changed", self.on_uploaded_changed)

    def on_uploaded_changed(self, event, uploaded):
        self.task.uploaded = uploaded

class DownloadControllerReceiver(Receiver):
    def __init__(self, task):
        Receiver.__init__(self)

        self.task = task

        self.add_callback("downloaded_changed", self.on_downloaded_changed)

    def on_downloaded_changed(self, event, downloaded):
        self.task.downloaded = downloaded

class DownloadTask(Task):
    def __init__(self, target):
        Task.__init__(self)

        self.type = None # "f" or "d"
        self.parent = target
        self.src = None
        self.dst = None
        self.src_path = ""
        self.dst_path = ""
        self.download_size = 0
        self.upload_size = 0
        self.modified = 0
        self._downloaded = 0
        self._uploaded = 0

        self.upload_controller = None
        self.download_controller = None

        self.worker = None

        def on_status_changed(event):
            if self.status != "pending":
                if self.upload_controller is not None:
                    self.upload_controller.stop()

                if self.download_controller is not None:
                    self.download_controller.stop()

        status_receiver = Receiver()
        status_receiver.add_callback("status_changed", on_status_changed)

        self.add_receiver(status_receiver)

        self.add_event("downloaded_changed")
        self.add_event("uploaded_changed")

    @property
    def downloaded(self):
        return self._downloaded

    @downloaded.setter
    def downloaded(self, value):
        old_value = self._downloaded
        self._downloaded = value

        if old_value != value:
            self.emit_event("downloaded_changed")

            if self.parent is not None:
                self.parent.downloaded += value - old_value

    @property
    def uploaded(self):
        return self._uploaded

    @uploaded.setter
    def uploaded(self, value):
        old_value = self._uploaded
        self._uploaded = value

        if old_value != value:
            self.emit_event("uploaded_changed")

    def stop_condition(self):
        if self.worker.stopped:
            return True

        if self.parent.stop_condition():
            return True

        return self.status not in (None, "pending")

    def recursive_mkdir(self, path):
        path = Paths.join_properly("/", path)

        p = "/"

        for i in path.split("/"):
            if not i:
                continue

            p = Paths.join(p, i)

            try:
                self.dst.mkdir(p)
            except (FileExistsError, PermissionError):
                pass

    def check_if_download(self):
        try:
            meta = self.dst.get_meta(self.dst_path)
        except FileNotFoundError:
            return True

        if not meta["type"]:
            return True

        size1 = meta["size"] or 0
        modified1 = meta["modified"] or 0

        size2 = self.download_size
        modified2 = self.modified

        if self.src.is_encrypted(self.src_path):
            if not self.dst.is_encrypted(self.dst_path):
                size2 = max(size2 - MIN_ENC_SIZE, 0)
                size1 = pad_size(size1)
        elif self.dst.is_encrypted(self.dst_path):
            size1 = max(size1 - MIN_ENC_SIZE, 0)
            size2 = pad_size(size2)

        return size1 != size2 or modified1 < modified2

    def get_download_size(self):
        if self.src.is_encrypted(self.src_path):
            flist = FileList(self.parent.name,
                             self.src.storage.name,
                             self.parent.downloader.directory)

            node = flist.find_node(self.src_path)
            if node["padded_size"]:
                return node["padded_size"] + MIN_ENC_SIZE

            return self.download_size
        else:
            return self.src.get_meta(self.src_path)["size"] or 0

    def download_file(self):
        if self.dst.is_dir(self.dst_path):
            name = Paths.split(self.src_path)[1]
            self.dst_path = Paths.join(self.dst_path, name)

        if self.stop_condition():
            return

        if not self.src.is_encrypted(self.src_path):
            # In this case the size was not determined yet
            try:
                self.download_size = self.get_download_size()
            except FileNotFoundError:
                self.status = "failed"
                return

        if not self.check_if_download():
            self.status = "finished"
            return

        if self.stop_condition():
            return

        self.recursive_mkdir(Paths.split(self.dst_path)[0])

        if self.stop_condition():
            return

        if self.dst.is_encrypted(self.dst_path):
            download_generator = self.src.get_encrypted_file(self.src_path)
        else:
            download_generator = self.src.get_file(self.src_path)

        self.download_controller = next(download_generator)
        if self.download_controller is not None:
            self.download_controller.add_receiver(DownloadControllerReceiver(self))

        if self.stop_condition():
            return

        try:
            tmpfile = next(download_generator)

            if self.download_controller is None:
                self.downloaded = self.download_size

            if not self.upload_size:
                self.upload_size = get_file_size(tmpfile)

            self.upload_controller, ivs = self.dst.upload(tmpfile, self.dst_path)

            if self.stop_condition():
                return

            self.upload_controller.add_receiver(UploadControllerReceiver(self))
            self.upload_controller.work()

            self.status = "finished"
        except ControllerInterrupt:
            return

    def complete(self, worker):
        self.worker = worker

        if self.stop_condition():
            return True

        self.status = "pending"

        if self.type == "d":
            self.recursive_mkdir(self.dst_path)
        else:
            self.download_file()

        if self.stop_condition():
            return True

        self.status = "finished"
