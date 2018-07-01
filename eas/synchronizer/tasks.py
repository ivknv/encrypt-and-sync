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

__all__ = ["SyncTask", "UploadTask", "MkdirTask", "RmTask", "ModifiedTask",
           "ChmodTask", "ChownTask", "CreateSymlinkTask"]

class UploadTaskReceiver(Receiver):
    def __init__(self, task):
        Receiver.__init__(self)

        self.weak_task = weakref.finalize(task, lambda: None)

    def on_uploaded_changed(self, event, uploaded):
        result = self.weak_task.peek()

        if result is None:
            return False

        task = result[0]
        task.uploaded = uploaded

class DownloadTaskReceiver(Receiver):
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
        self.link_path = None
        self.modified = None
        self.mode = None
        self.owner = None
        self.group = None

        self._uploaded = 0
        self._downloaded = 0

        self.config = target.config

        self.upload_limit = float("inf") # Bytes per second
        self.download_limit = float("inf") # Bytes per second

        self.src_flist = target.shared_flist1
        self.dst_flist = target.shared_flist2

        self.src = target.src
        self.dst = target.dst

        self.add_receiver(TaskFailLogReceiver())

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

    def run(self):
        try:
            return super().run()
        except (KeyboardInterrupt, ControllerInterrupt):
            return True

class UploadTask(SyncTask):
    def __init__(self, *args, **kwargs):
        self.upload_task = None
        self.download_task = None
        self._upload_limit = float("inf")
        self._download_limit = float("inf")

        SyncTask.__init__(self, *args, **kwargs)

    @property
    def upload_limit(self):
        return self._upload_limit

    @upload_limit.setter
    def upload_limit(self, value):
        self._upload_limit = value

        if self.upload_task is not None:
            self.upload_task.limit = self.upload_limit

    @property
    def download_limit(self):
        return self._download_limit

    @download_limit.setter
    def download_limit(self, value):
        self._download_limit = value

        if self.download_task is not None:
            self.download_task.limit = self.download_limit

    def stop(self):
        super().stop()

        upload_task = self.upload_task
        download_task = self.download_task

        if upload_task is not None:
            upload_task.stop()

        if download_task is not None:
            download_task.stop()

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

            self.download_task = next(download_generator)
            if self.download_task is not None:
                self.download_task.add_receiver(DownloadTaskReceiver(self))

            try:
                temp_file = next(download_generator)
            except FileNotFoundError:
                self.src_flist.remove(full_src_path)

                self.status = "skipped"

                self.autocommit()

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

            task, ivs = self.dst.upload(temp_file, dst_path,
                                        timeout=upload_timeout,
                                        limit=self.upload_limit)

            self.upload_task = task
            task.add_receiver(UploadTaskReceiver(self))

            if self.stopped:
                return True

            task.run()

            mode = owner = group = None

            if self.dst.storage.persistent_mode:
                dst_node = self.dst_flist.find(full_dst_path)
                mode = dst_node["mode"]
                owner = dst_node["owner"]
                group = dst_node["group"]

            modified = time.mktime(time.gmtime())

            newnode = {"type":        "f",
                       "path":        full_dst_path,
                       "padded_size": padded_size,
                       "modified":    modified,
                       "mode":        mode,
                       "owner":       owner,
                       "group":       group,
                       "link_path":   None,
                       "IVs":         ivs}

            self.dst_flist.insert(newnode)
            self.dst_flist.update_modified(pathm.dirname(full_dst_path), modified)

            self.status = "finished"

            self.autocommit()

            return True
        except ControllerInterrupt:
            return True
        finally:
            self.upload_task = None
            self.download_task = None

class CreateSymlinkTask(SyncTask):
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

        ivs = self.dst.create_symlink(dst_path, self.link_path)

        modified = time.mktime(time.gmtime())

        newnode = {"type":        "f",
                   "path":        full_dst_path,
                   "modified":    modified,
                   "mode":        None,
                   "padded_size": 0,
                   "link_path":   self.link_path,
                   "IVs":         ivs}

        self.dst_flist.insert(newnode)
        self.dst_flist.update_modified(pathm.dirname(full_dst_path), modified)

        self.status = "finished"

        self.autocommit()

        return True

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

        modified = time.mktime(time.gmtime())

        newnode = {"type":        "d",
                   "path":        full_dst_path,
                   "modified":    modified,
                   "mode":        None,
                   "padded_size": 0,
                   "link_path":   None,
                   "IVs":         ivs}

        self.dst_flist.insert(newnode)
        self.dst_flist.update_modified(pathm.dirname(full_dst_path), modified)

        self.status = "finished"

        self.autocommit()

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
            removed = True
        except FileNotFoundError:
            removed = False

        if self.node_type == "f":
            self.dst_flist.remove(full_dst_path)
        else:
            self.dst_flist.remove_recursively(full_dst_path)

        if removed:
            modified = time.mktime(time.gmtime())
            self.dst_flist.update_modified(pathm.dirname(full_dst_path), modified)

        self.status = "finished"

        self.autocommit()

        return True

class ModifiedTask(SyncTask):
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

        assert(self.modified is not None)

        try:
            self.dst.set_modified(dst_path, self.modified)
            self.dst_flist.update_modified(full_dst_path, self.modified)

            self.status = "finished"
        except FileNotFoundError:
            self.dst_flist.remove_recursively(full_dst_path)

            self.status = "skipped"

        self.autocommit()

        return True

class ChmodTask(SyncTask):
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

        assert(self.mode is not None)

        try:
            self.dst.chmod(dst_path, self.mode)
            self.dst_flist.update_mode(full_dst_path, self.mode)

            self.status = "finished"
        except FileNotFoundError:
            self.dst_flist.remove_recursively(full_dst_path)

            self.status = "skipped"

        self.autocommit()

        return True

class ChownTask(SyncTask):
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

        assert(self.owner is not None or self.group is not None)

        try:
            self.dst.chown(dst_path, self.owner, self.group)

            if self.owner is not None:
                self.dst_flist.update_owner(full_dst_path, self.owner)

            if self.group is not None:
                self.dst_flist.update_group(full_dst_path, self.group)

            self.status = "finished"
        except FileNotFoundError:
            self.dst_flist.remove_recursively(full_dst_path)

            self.status = "skipped"

        self.autocommit()

        return True
