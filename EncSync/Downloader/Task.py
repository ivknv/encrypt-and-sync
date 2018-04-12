#!/usr/bin/env python
# -*- coding: utf-8 -*-

import weakref

from ..Task import Task
from ..Event.Receiver import Receiver
from ..common import get_file_size
from ..Storage.Exceptions import ControllerInterrupt
from .. import Paths

__all__ = ["DownloadTask"]

class UploadControllerReceiver(Receiver):
    def __init__(self, task):
        Receiver.__init__(self)

        self.weak_task = weakref.finalize(task, lambda: None)

    def on_uploaded_changed(self, event, uploaded):
        result = self.weak_task.peek()

        if result is None:
            return False

        task = result[0]
        task.uploaded = uploaded

class DownloadControllerReceiver(Receiver):
    def __init__(self, task):
        Receiver.__init__(self)

        self.weak_task = weakref.finalize(task, lambda: None)

    def on_downloaded_changed(self, event, downloaded):
        result = self.weak_task.peek()

        if result is None:
            return False

        task = result[0]
        task.downloaded = downloaded

class DownloadTask(Task):
    """
        Events: downloaded_changed, uploaded_changed
    """

    def __init__(self, target):
        Task.__init__(self)

        self.type = None # "f" or "d"
        self.parent = target
        self.src = None
        self.dst = None
        self.IVs = b""
        self.src_path = ""
        self.dst_path = ""
        self.download_size = 0
        self.upload_size = 0
        self.modified = 0
        self._downloaded = 0
        self._uploaded = 0

        self.upload_controller = None
        self.download_controller = None

        self._upload_limit = target.upload_limit
        self._download_limit = target.download_limit

        self.worker = None

    @property
    def upload_limit(self):
        return self._upload_limit

    @upload_limit.setter
    def upload_limit(self, value):
        self._upload_limit = value

        if self.upload_controller is not None:
            self.upload_controller.limit = value

    @property
    def download_limit(self):
        return self._download_limit

    @download_limit.setter
    def download_limit(self, value):
        self._download_limit = value

        if self.download_controller is not None:
            self.download_controller.limit = value

    def stop(self):
        Task.stop(self)

        if self.upload_controller is not None:
            self.upload_controller.stop()

        if self.download_controller is not None:
            self.download_controller.stop()

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
        if self.stopped or self.worker.stopped:
            return True

        if self.parent.stop_condition():
            return True

        return self.status not in (None, "pending")

    def recursive_mkdir(self, path):
        path = Paths.join_properly("/", path)

        p = "/"

        created = False

        for i in path.split("/"):
            if not i:
                continue

            p = Paths.join(p, i)

            try:
                self.dst.mkdir(p)
            except (FileExistsError, PermissionError):
                created = False
            else:
                created = True

        return created

    def check_if_download(self):
        try:
            meta = self.dst.get_meta(self.dst_path)
        except FileNotFoundError:
            return True

        if not meta["type"]:
            return True

        modified1 = meta["modified"] or 0
        modified2 = self.modified

        return modified1 < modified2

    def download_file(self):
        if self.dst.is_dir(self.dst_path):
            name = Paths.split(self.src_path)[1]
            self.dst_path = Paths.join(self.dst_path, name)

        if self.stop_condition():
            return

        if not self.check_if_download():
            self.status = "skipped"
            return

        if self.stop_condition():
            return

        self.recursive_mkdir(Paths.split(self.dst_path)[0])

        if self.stop_condition():
            return

        try:
            if self.dst.is_encrypted(self.dst_path):
                if self.parent.expected_total_children == -1:
                    download_generator = self.src.get_encrypted_file(self.src_path, ivs=self.IVs)
                else:
                    download_generator = self.src.get_encrypted_file(self.src_path)
            else:
                if self.parent.expected_total_children == -1:
                    download_generator = self.src.get_file(self.src_path, ivs=self.IVs)
                else:
                    download_generator = self.src.get_file(self.src_path)

            self.download_controller = next(download_generator)
            if self.download_controller is not None:
                self.download_controller.limit = self.download_limit
                self.download_controller.add_receiver(DownloadControllerReceiver(self))

                self.download_controller.begin()
                self.download_size = self.download_controller.size

            if self.stop_condition():
                return

            tmpfile = next(download_generator)

            if self.download_controller is None:
                self.downloaded = self.download_size

            if not self.upload_size:
                self.upload_size = get_file_size(tmpfile)

            self.upload_controller, ivs = self.dst.upload(tmpfile, self.dst_path)
            self.upload_controller.limit = self.upload_limit

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
            if not self.recursive_mkdir(self.dst_path):
                self.status = "skipped"
        else:
            self.download_file()

        if self.stop_condition():
            return True

        if self.status in ("pending", None):
            self.status = "finished"
