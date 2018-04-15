# -*- coding: utf-8 -*-

import time
import weakref

from .Logging import TaskFailLogReceiver

from ..Event.Receiver import Receiver
from ..Task import Task
from ..Encryption import pad_size, MIN_ENC_SIZE
from ..common import get_file_size
from ..Storage.Exceptions import ControllerInterrupt
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

        self.flist1 = target.shared_flist1
        self.flist2 = target.shared_flist2

        self.src = target.src
        self.dst = target.dst

        self.add_receiver(TaskFailLogReceiver())

    def stop_condition(self):
        if self.stopped or self.parent.stop_condition():
            return True

        return self.status not in (None, "pending")

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

    def complete(self, worker):
        try:
            if self.stop_condition():
                return True

            self.status = "pending"

            src_path = Paths.join(self.src.prefix, self.path)
            dst_path = Paths.join(self.dst.prefix, self.path)

            upload_timeout = self.config.upload_timeout

            if self.dst.encrypted:
                download_generator = self.src.get_encrypted_file(self.path,
                                                                 timeout=self.config.timeout,
                                                                 limit=self.download_limit)
            else:
                download_generator = self.src.get_file(self.path,
                                                       timeout=self.config.timeout,
                                                       limit=self.download_limit)

            self.download_controller = next(download_generator)
            if self.download_controller is not None:
                self.download_controller.add_receiver(DownloadControllerReceiver(self))

            try:
                temp_file = next(download_generator)
            except FileNotFoundError:
                self.flist1.remove_node(src_path)
                self.autocommit()

                self.status = "skipped"
                return True

            if self.stop_condition():
                return True

            self.size = get_file_size(temp_file)

            if self.dst.encrypted:
                padded_size = max(self.size - MIN_ENC_SIZE, 0)
            else:
                padded_size = pad_size(self.size)

            if self.size >= 700 * 1024**2:
                if not isinstance(upload_timeout, (tuple, list)):
                    connect_timeout = read_timeout = upload_timeout
                else:
                    connect_timeout, read_timeout = upload_timeout

                new_read_timeout = 300.0

                if read_timeout < new_read_timeout:
                    upload_timeout = (connect_timeout, new_read_timeout)

            controller, ivs = self.dst.upload(temp_file, self.path,
                                              timeout=upload_timeout,
                                              limit=self.upload_limit)

            self.upload_controller = controller
            controller.add_receiver(UploadControllerReceiver(self))

            if self.stop_condition():
                return True

            controller.work()

            newnode = {"type":        "f",
                       "path":        dst_path,
                       "padded_size": padded_size,
                       "modified":    time.mktime(time.gmtime()),
                       "IVs":         ivs}

            self.flist2.insert_node(newnode)
            self.autocommit()

            self.status = "finished"

            return True
        except ControllerInterrupt:
            return True
        finally:
            self.upload_controller = None
            self.download_controller = None

class MkdirTask(SyncTask):
    def complete(self, worker):
        if self.stop_condition():
            return True

        self.status = "pending"
        src_path = Paths.join(self.src.prefix, self.path)
        dst_path = Paths.join(self.dst.prefix, self.path)

        ivs = self.dst.mkdir(self.path)

        newnode = {"type":        "d",
                   "path":        dst_path,
                   "modified":    time.mktime(time.gmtime()),
                   "padded_size": 0,
                   "IVs":         ivs}

        self.flist2.insert_node(newnode)
        self.autocommit()

        self.status = "finished"

        return True

class RmTask(SyncTask):
    def complete(self, worker):
        if self.stop_condition():
            return True

        self.status = "pending"

        dst_path = Paths.join(self.dst.prefix, self.path)

        try:
            self.dst.remove(self.path)
        except FileNotFoundError:
            pass

        self.flist2.remove_node_children(dst_path)
        self.flist2.remove_node(dst_path)
        self.autocommit()

        self.status = "finished"

        return True
