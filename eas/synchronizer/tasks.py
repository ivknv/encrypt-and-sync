# -*- coding: utf-8 -*-

import time
import weakref

from .logging import TaskFailLogReceiver

from ..events import Receiver
from ..task import Task
from ..encryption import pad_size, MIN_ENC_SIZE
from ..common import get_file_size
from ..storage.exceptions import ControllerInterrupt
from .. import Paths

__all__ = ["SyncTask", "UploadTask", "MkdirTask", "RmTask"]

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

class SyncTask(Task):
    """
        Events: uploaded_changed, downloaded_changed, filename_too_long, interrupted
    """

    def __init__(self, target):
        self._stopped = False

        Task.__init__(self)

        self.parent = target
        self.type = None # "new", "update" or "rm"
        self.node_type = None # "f" or "d"
        self.path = None
        self.size = 0
        self._uploaded = 0
        self._downloaded = 0

        self.config = target.config

        self.upload_limit = float("inf") # Bytes per second
        self.download_limit = float("inf") # Bytes per second

        self.dst_flist = target.shared_flist2

        self.src = target.src
        self.dst = target.dst

        self.add_receiver(TaskFailLogReceiver())

    @property
    def stopped(self):
        if self._stopped or self.parent.stopped:
            return True

        return self.status not in (None, "pending")

    @stopped.setter
    def stopped(self, value):
        self._stopped = value

    @property
    def uploaded(self):
        return self._uploaded

    @uploaded.setter
    def uploaded(self, value):
        old_value = self._uploaded
        self._uploaded = value
        if value != old_value:
            self.emit_event("uploaded_changed")

    @property
    def downloaded(self):
        return self._downloaded

    @downloaded.setter
    def downloaded(self, value):
        old_value = self._downloaded
        self._downloaded = value

        if value != old_value:
            self.emit_event("downloaded_changed")

    def autocommit(self):
        self.parent.autocommit()

class UploadTask(SyncTask):
    def __init__(self, *args, **kwargs):
        self.upload_controller = None
        self.download_controller = None
        self._upload_limit = float("inf")
        self._download_limit = float("inf")

        SyncTask.__init__(self, *args, **kwargs)

    @property
    def upload_limit(self):
        return self._upload_limit

    @upload_limit.setter
    def upload_limit(self, value):
        self._upload_limit = value

        if self.upload_controller is not None:
            self.upload_controller.limit = self.upload_limit

    @property
    def download_limit(self):
        return self._download_limit

    @download_limit.setter
    def download_limit(self, value):
        self._download_limit = value

        if self.download_controller is not None:
            self.download_controller.limit = self.download_limit

    def stop(self):
        SyncTask.stop(self)

        if self.upload_controller is not None:
            self.upload_controller.stop()

        if self.download_controller is not None:
            self.download_controller.stop()

    def complete(self):
        try:
            if self.stopped:
                return True

            self.status = "pending"

            src_subpath = self.parent.subpath1
            dst_subpath = self.parent.subpath2

            src_path = Paths.join(src_subpath, self.path)
            dst_path = Paths.join(dst_subpath, self.path)

            full_src_path = Paths.join(self.src.prefix, src_path)
            full_dst_path = Paths.join(self.dst.prefix, dst_path)

            upload_timeout = self.config.upload_timeout

            if self.dst.encrypted:
                download_generator = self.src.get_encrypted_file(src_path,
                                                                 timeout=self.config.timeout,
                                                                 limit=self.download_limit)
            else:
                download_generator = self.src.get_file(src_path,
                                                       timeout=self.config.timeout,
                                                       limit=self.download_limit)

            self.download_controller = next(download_generator)
            if self.download_controller is not None:
                self.download_controller.add_receiver(DownloadControllerReceiver(self))

            try:
                temp_file = next(download_generator)
            except FileNotFoundError:
                self.status = "skipped"
                return True

            if self.stopped:
                return True

            self.size = get_file_size(temp_file)

            if self.dst.encrypted:
                padded_size = max(self.size - MIN_ENC_SIZE, 0)
            else:
                padded_size = pad_size(self.size)

            # Timeout fix for Yandex.Disk
            if self.size >= 700 * 1024**2 and self.dst.storage.type == "yadisk":
                if not isinstance(upload_timeout, (tuple, list)):
                    connect_timeout = read_timeout = upload_timeout
                else:
                    connect_timeout, read_timeout = upload_timeout

                new_read_timeout = 500.0

                if read_timeout is not None and read_timeout < new_read_timeout:
                    upload_timeout = (connect_timeout, new_read_timeout)

            controller, ivs = self.dst.upload(temp_file, dst_path,
                                              timeout=upload_timeout,
                                              limit=self.upload_limit)

            self.upload_controller = controller
            controller.add_receiver(UploadControllerReceiver(self))

            if self.stopped:
                return True

            controller.work()

            modified = None

            src_filelist = self.parent.shared_flist1

            if self.parent.preserve_modified and self.dst.storage.supports_set_modified:
                modified = src_filelist.find_node(full_src_path)["modified"]

                if modified is not None:
                    self.dst.set_modified(dst_path, modified)

                # Preserve parent modified date
                if dst_path not in ("", "/"):
                    parent_modified = src_filelist.find_node(Paths.split(full_src_path)[0])["modified"]

                    if parent_modified not in (None, 0):
                        self.dst.set_modified(Paths.split(dst_path)[0], parent_modified)

            if modified is None:
                modified = time.mktime(time.gmtime())

            newnode = {"type":        "f",
                       "path":        full_dst_path,
                       "padded_size": padded_size,
                       "modified":    modified,
                       "IVs":         ivs}

            self.dst_flist.insert_node(newnode)
            self.autocommit()

            self.status = "finished"

            return True
        except ControllerInterrupt:
            return True
        finally:
            self.upload_controller = None
            self.download_controller = None

class MkdirTask(SyncTask):
    def complete(self):
        if self.stopped:
            return True

        self.status = "pending"

        src_subpath = self.parent.subpath1
        dst_subpath = self.parent.subpath2

        src_path = Paths.join(src_subpath, self.path)
        dst_path = Paths.join(dst_subpath, self.path)

        full_src_path = Paths.join(self.src.prefix, src_path)
        full_dst_path = Paths.join(self.dst.prefix, dst_path)

        ivs = self.dst.mkdir(dst_path)

        src_filelist = self.parent.shared_flist1

        modified = None

        if self.parent.preserve_modified and self.dst.storage.supports_set_modified:
            modified = src_filelist.find_node(full_src_path)["modified"]

            if modified is not None:
                self.dst.set_modified(dst_path, modified)

            # Preserve parent modified date
            if dst_path not in ("", "/"):
                parent_modified = src_filelist.find_node(Paths.split(full_src_path)[0])["modified"]

                if parent_modified not in (None, 0):
                    self.dst.set_modified(Paths.split(dst_path)[0], parent_modified)

        if modified is None:
            modified = time.mktime(time.gmtime())

        newnode = {"type":        "d",
                   "path":        full_dst_path,
                   "modified":    modified,
                   "padded_size": 0,
                   "IVs":         ivs}

        self.dst_flist.insert_node(newnode)
        self.autocommit()

        self.status = "finished"

        return True

class RmTask(SyncTask):
    def complete(self):
        if self.stopped:
            return True

        self.status = "pending"

        src_subpath = self.parent.subpath1
        dst_subpath = self.parent.subpath2

        src_path = Paths.join(src_subpath, self.path)
        dst_path = Paths.join(dst_subpath, self.path)

        full_src_path = Paths.join(self.src.prefix, src_path)
        full_dst_path = Paths.join(self.dst.prefix, dst_path)

        try:
            self.dst.remove(dst_path)
        except FileNotFoundError:
            pass

        if self.node_type == "d":
            self.dst_flist.remove_node_children(full_dst_path)

        src_filelist = self.parent.shared_flist1

        # Preserve parent modified date
        if self.parent.preserve_modified and dst_path not in ("", "/"):
            if self.dst.storage.supports_set_modified:
                parent_modified = src_filelist.find_node(Paths.split(full_src_path)[0])["modified"]

                if parent_modified not in (None, 0):
                    self.dst.set_modified(Paths.split(dst_path)[0], parent_modified)

        self.dst_flist.remove_node(full_dst_path)
        self.autocommit()

        self.status = "finished"

        return True
