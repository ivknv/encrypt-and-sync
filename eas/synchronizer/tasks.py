# -*- coding: utf-8 -*-

import time
import weakref

from .logging import TaskFailLogReceiver

from ..events import Receiver
from ..task import Task
from ..encryption import pad_size, MIN_ENC_SIZE
from ..common import get_file_size
from ..storage.exceptions import ControllerInterrupt
from .. import pathm

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

        if task.stopped:
            event.emitter.stop()

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

        if task.stopped:
            event.emitter.stop()

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

        upload_controller = self.upload_controller
        download_controller = self.download_controller

        if upload_controller is not None:
            upload_controller.stop()

        if download_controller is not None:
            download_controller.stop()

    def complete(self):
        try:
            if self.stopped:
                return True

            self.status = "pending"

            src_subpath = self.parent.subpath1
            dst_subpath = self.parent.subpath2

            src_path = pathm.join(src_subpath, self.path)
            dst_path = pathm.join(dst_subpath, self.path)

            full_src_path = pathm.join(self.src.prefix, src_path)
            full_dst_path = pathm.join(self.dst.prefix, dst_path)

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
            if self.size >= 700 * 1024**2 and self.dst.storage.name == "yadisk":
                if not isinstance(upload_timeout, (tuple, list)):
                    connect_timeout = read_timeout = upload_timeout
                else:
                    connect_timeout, read_timeout = upload_timeout

                new_read_timeout = 300.0

                if read_timeout is not None and read_timeout < new_read_timeout:
                    upload_timeout = (connect_timeout, new_read_timeout)

                # Workaround for https://bugs.python.org/issue33838
                if upload_timeout == (None, None):
                    upload_timeout = None

            controller, ivs = self.dst.upload(temp_file, dst_path,
                                              timeout=upload_timeout,
                                              limit=self.upload_limit)

            self.upload_controller = controller
            controller.add_receiver(UploadControllerReceiver(self))

            if self.stopped:
                return True

            controller.work()

            src_node = None
            modified = None
            mode = None

            src_filelist = self.parent.shared_flist1

            if self.dst.storage.supports_chmod:
                src_node = src_filelist.find(full_src_path)
                mode = src_node["mode"]

                self.dst.chmod(dst_path, mode, ivs=ivs)

            if self.parent.preserve_modified and self.dst.storage.supports_set_modified:
                if src_node is None:
                    src_node = src_filelist.find(full_src_path)

                modified = src_node["modified"]

                if modified is not None:
                    self.dst.set_modified(dst_path, modified, ivs=ivs)

                # Preserve parent modified date
                if dst_path not in ("", "/"):
                    parent_modified = src_filelist.find(pathm.split(full_src_path)[0])["modified"]
                    parent_ivs = ivs[0:-16]

                    if parent_modified not in (None, 0):
                        self.dst.set_modified(pathm.split(dst_path)[0], parent_modified, ivs=parent_ivs)

            if modified is None:
                modified = time.mktime(time.gmtime())

            newnode = {"type":        "f",
                       "path":        full_dst_path,
                       "padded_size": padded_size,
                       "modified":    modified,
                       "mode":        mode,
                       "IVs":         ivs}

            self.dst_flist.insert(newnode)
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

        src_path = pathm.join(src_subpath, self.path)
        dst_path = pathm.join(dst_subpath, self.path)

        full_src_path = pathm.join(self.src.prefix, src_path)
        full_dst_path = pathm.join(self.dst.prefix, dst_path)

        ivs = self.dst.mkdir(dst_path)

        src_filelist = self.parent.shared_flist1

        src_node = None
        modified = None
        mode = None

        if self.dst.storage.supports_chmod:
            src_node = src_filelist.find(full_src_path)
            mode = src_node["mode"]

            self.dst.chmod(dst_path, mode, ivs=ivs)

        if self.parent.preserve_modified and self.dst.storage.supports_set_modified:
            if src_node is None:
                src_filelist.find(full_src_path)

            modified = src_node["modified"]

            if modified is not None:
                self.dst.set_modified(dst_path, modified, ivs=ivs)

            # Preserve parent modified date
            if dst_path not in ("", "/"):
                parent_modified = src_filelist.find(pathm.split(full_src_path)[0])["modified"]
                parent_ivs = ivs[0:-16]

                if parent_modified not in (None, 0):
                    self.dst.set_modified(pathm.split(dst_path)[0], parent_modified, ivs=parent_ivs)

        if modified is None:
            modified = time.mktime(time.gmtime())

        newnode = {"type":        "d",
                   "path":        full_dst_path,
                   "modified":    modified,
                   "mode":        mode,
                   "padded_size": 0,
                   "IVs":         ivs}

        self.dst_flist.insert(newnode)
        self.autocommit()

        self.status = "finished"

        return True

class RmTask(SyncTask):
    def complete(self):
        if self.stopped:
            return True

        assert(self.node_type in ("f", "d"))

        self.status = "pending"

        src_subpath = self.parent.subpath1
        dst_subpath = self.parent.subpath2

        src_path = pathm.join(src_subpath, self.path)
        dst_path = pathm.join(dst_subpath, self.path)

        full_src_path = pathm.join(self.src.prefix, src_path)
        full_dst_path = pathm.join(self.dst.prefix, dst_path)

        try:
            self.dst.remove(dst_path)
        except FileNotFoundError:
            pass

        if self.node_type == "f":
            self.dst_flist.remove(full_dst_path)
        else:
            self.dst_flist.remove_recursively(full_dst_path)

        src_filelist = self.parent.shared_flist1

        # Preserve parent modified date
        if self.parent.preserve_modified and dst_path not in ("", "/"):
            if self.dst.storage.supports_set_modified:
                parent_modified = src_filelist.find(pathm.split(full_src_path)[0])["modified"]
                parent_ivs = dst_filelist.find(pathm.split(full_dst_path)[0])["IVs"]

                if parent_modified not in (None, 0):
                    self.dst.set_modified(pathm.split(dst_path)[0], parent_modified, ivs=parent_ivs)

        self.autocommit()

        self.status = "finished"

        return True
