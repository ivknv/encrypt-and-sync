# -*- coding: utf-8 -*-

from datetime import datetime, timezone
import os
import shutil
import stat
import sys
import time

from .. import pathm
from ..common import is_windows, get_file_size
from ..constants import PERMISSION_MASK

from .storage import Storage
from .exceptions import ControllerInterrupt
from .download_task import DownloadTask
from .upload_task import UploadTask

__all__ = ["LocalStorage"]

MIN_READ_SIZE = 4 * 1024**2 # Bytes

if is_windows():
    def _is_reparse_point(stat_result):
        return stat_result.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
else:
    def _is_reparse_point(stat_result):
        return False

def utc_to_local(utc_timestamp):
    return datetime.fromtimestamp(utc_timestamp).replace(tzinfo=timezone.utc).astimezone(tz=None).timestamp()

def local_to_utc(local_timestamp):
    try:
        return max(time.mktime(time.gmtime(local_timestamp)), 0)
    except (OSError, OverflowError):
        return 0

class LocalDownloadTask(DownloadTask):
    def __init__(self, config, in_path, out_file, **kwargs):
        super().__init__(config, out_file, **kwargs)

        self.in_path = in_path

    def begin(self):
        if self.size is None:
            self.size = get_file_size(self.in_path)

    def complete(self):
        try:
            self.status = "pending"

            if self.stopped:
                raise ControllerInterrupt

            self.begin()

            if self.stopped:
                raise ControllerInterrupt

            with open(self.in_path, "rb") as in_file:
                while True:
                    if self.stopped:
                        raise ControllerInterrupt

                    content = in_file.read(MIN_READ_SIZE)

                    if self.stopped:
                        raise ControllerInterrupt

                    if not content:
                        break

                    self.out_file.write(content)
                    self.downloaded += len(content)

            self.status = "finished"
        except Exception as e:
            self.status = "failed"

            raise e

class LocalUploadTask(UploadTask):
    def __init__(self, config, in_file, out_path, **kwargs):
        super().__init__(config, in_file, **kwargs)

        self.out_path = out_path

    def complete(self):
        try:
            self.status = "pending"

            if self.stopped:
                raise ControllerInterrupt

            with open(self.out_path, "wb") as out_file:
                while True:
                    if self.stopped:
                        raise ControllerInterrupt

                    content = self.in_file.read(MIN_READ_SIZE)

                    if self.stopped:
                        raise ControllerInterrupt

                    if not content:
                        break

                    out_file.write(content)
                    self.uploaded += len(content)

            self.status = "finished"
        except Exception as e:
            self.status = "failed"

            raise e

class LocalStorage(Storage):
    name = "local"
    type = "local"
    case_sensitive = not is_windows()
    parallelizable = False

    supports_set_modified = True
    supports_chmod = not is_windows() and hasattr(os, "chmod")
    supports_chown = not is_windows()
    supports_symlinks = not is_windows()
    persistent_mode = True

    def get_meta(self, path, *args, **kwargs):
        path = pathm.to_sys(path)
        filename = os.path.split(path)[1]

        s = os.lstat(path)

        meta = {"type":     None,
                "name":     filename,
                "modified": 0,
                "size":     0,
                "mode":     None,
                "owner":    None,
                "group":    None,
                "link":     None}

        if stat.S_ISREG(s.st_mode):
            meta["type"]     = "file"
            meta["size"]     = s.st_size
        elif stat.S_ISDIR(s.st_mode):
            if _is_reparse_point(s):
                return meta

            meta["type"]     = "dir"
        elif stat.S_ISLNK(s.st_mode):
            meta["type"]     = "file"
            meta["link"]     = pathm.from_sys(os.readlink(path))
        else:
            return meta

        meta["modified"] = local_to_utc(s.st_mtime)

        if not is_windows():
            meta["mode"]  = s.st_mode & PERMISSION_MASK
            meta["owner"] = s.st_uid
            meta["group"] = s.st_gid

        return meta

    def listdir(self, path, *args, **kwargs):
        with os.scandir(pathm.to_sys(path)) as it:
            for entry in it:
                link_path = None
                meta = {"type":     None,
                        "name":     entry.name,
                        "modified": 0,
                        "size":     0,
                        "mode":     None,
                        "owner":    None,
                        "group":    None,
                        "link":     None}

                s = entry.stat(follow_symlinks=False)
                
                if entry.is_file(follow_symlinks=False):
                    meta["type"]     = "file"
                    meta["size"]     = s.st_size
                elif entry.is_dir(follow_symlinks=False):
                    if _is_reparse_point(s):
                        continue

                    meta["type"]     = "dir"
                elif entry.is_symlink():
                    meta["type"] = "file"
                    meta["link"] = pathm.from_sys(os.readlink(entry.path))

                meta["modified"] = local_to_utc(s.st_mtime)

                if not is_windows():
                    meta["mode"] = s.st_mode & PERMISSION_MASK
                    meta["owner"] = s.st_uid
                    meta["group"] = s.st_gid

                yield meta

    def mkdir(self, path, *args, **kwargs):
        os.mkdir(pathm.to_sys(path))

    def remove(self, path, *args, **kwargs):
        path = pathm.to_sys(path)

        try:
            shutil.rmtree(path)
        except NotADirectoryError:
            # os.remove() raises PermissionError when path is a directory
            os.remove(path)

    def upload(self, in_file, out_path, *args, **kwargs):
        out_path = pathm.to_sys(out_path)

        return LocalUploadTask(self.config, in_file, out_path)

    def download(self, in_path, out_file, *args, **kwargs):
        in_path = pathm.to_sys(in_path)

        return LocalDownloadTask(self.config, in_path, out_file)

    def is_file(self, path, *args, **kwargs):
        return os.path.isfile(pathm.to_sys(path))

    def is_dir(self, path, *args, **kwargs):
        return os.path.isdir(pathm.to_sys(path))

    def exists(self, path, *args, **kwargs):
        return os.path.lexists(pathm.to_sys(path))

    def set_modified(self, path, new_modified, *args, **kwargs):
        new_modified = utc_to_local(new_modified)

        if os.utime in os.supports_follow_symlinks:
            os.utime(pathm.to_sys(path), (new_modified, new_modified), follow_symlinks=False)
        else:
            os.utime(pathm.to_sys(path), (new_modified, new_modified))

    if supports_chmod:
        def chmod(self, path, mode, *args, **kwargs):
            if mode is None:
                return

            if os.chmod in os.supports_follow_symlinks:
                os.chmod(pathm.to_sys(path), mode, follow_symlinks=False)
            else:
                os.chmod(pathm.to_sys(path), mode)

    def chown(self, path, uid, gid, *args, **kwargs):
        if uid is None and gid is None:
            return

        if os.chown in os.supports_follow_symlinks:
            os.chown(pathm.to_sys(path), uid, gid, follow_symlinks=False)
        else:
            os.chown(pathm.to_sys(path), uid, gid)

    def create_symlink(self, path, link_path, *args, **kwargs):
        os.symlink(pathm.to_sys(link_path), pathm.to_sys(path))
