# -*- coding: utf-8 -*-

from datetime import datetime, timezone
import os
import shutil
import stat
import sys
import time

from .. import pathm
from ..common import is_windows, get_file_size

from .storage import Storage
from .exceptions import ControllerInterrupt
from .download_controller import DownloadController
from .upload_controller import UploadController

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

class LocalDownloadController(DownloadController):
    def __init__(self, config, in_path, out_file, **kwargs):
        DownloadController.__init__(self, config, out_file, **kwargs)

        self.in_path = in_path

    def begin(self):
        if self.size is None:
            self.size = get_file_size(self.in_path)

    def work(self):
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

class LocalUploadController(UploadController):
    def __init__(self, config, in_file, out_path, **kwargs):
        UploadController.__init__(self, config, in_file, **kwargs)

        self.out_path = out_path

    def work(self):
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

class LocalStorage(Storage):
    name = "local"
    type = "local"
    case_sensitive = True
    parallelizable = False

    supports_set_modified = True
    supports_chmod = not is_windows() and hasattr(os, "chmod")
    supports_symlinks = not is_windows()
    persistent_mode = True

    def get_meta(self, path, *args, **kwargs):
        path = pathm.to_sys(path)
        filename = os.path.split(path)[1]

        s = os.lstat(path)
        link_path = None
        modified = 0
        size = 0
        mode = None

        if stat.S_ISREG(s.st_mode):
            resource_type = "file"
            size = s.st_size

            modified = local_to_utc(s.st_mtime)
        elif stat.S_ISDIR(s.st_mode):
            if _is_reparse_point(s):
                return {"type":     None,
                        "name":     filename,
                        "modified": 0,
                        "size":     0,
                        "mode":     None,
                        "link":     link_path}

            resource_type = "dir"
            size = 0
            modified = local_to_utc(s.st_mtime)
        elif stat.ISLNK(s.st_mode):
            resource_type = "file"
            link_path = pathm.from_sys(os.readlink(path))
            modified = local_to_utc(s.st_mtime)
        else:
            return {"type":     None,
                    "name":     filename,
                    "modified": 0,
                    "size":     0,
                    "mode":     None,
                    "link":     link_path}

        mode = s.st_mode

        return {"type":     resource_type,
                "name":     filename,
                "modified": modified,
                "size":     size,
                "mode":     mode,
                "link":     link_path}

    def listdir(self, path, *args, **kwargs):
        for entry in os.scandir(pathm.to_sys(path)):
            link_path = None
            
            if entry.is_file():
                resource_type = "file"
                size = entry.stat().st_size

                modified = local_to_utc(entry.stat().st_mtime)
            elif entry.is_dir():
                if _is_reparse_point(entry.stat()):
                    continue

                resource_type = "dir"
                size = 0
                modified = local_to_utc(entry.stat().st_mtime)
            else:
                continue

            if entry.is_symlink():
                resource_type = "file"
                size = 0
                link_path = pathm.from_sys(os.readlink(entry.path))

            mode = entry.stat().st_mode

            yield {"type":     resource_type,
                   "name":     entry.name,
                   "modified": modified,
                   "size":     size,
                   "mode":     mode,
                   "link":     link_path}

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

        return LocalUploadController(self.config, in_file, out_path)

    def download(self, in_path, out_file, *args, **kwargs):
        in_path = pathm.to_sys(in_path)

        return LocalDownloadController(self.config, in_path, out_file)

    def is_file(self, path, *args, **kwargs):
        return os.path.isfile(pathm.to_sys(path))

    def is_dir(self, path, *args, **kwargs):
        return os.path.isdir(pathm.to_sys(path))

    def exists(self, path, *args, **kwargs):
        return os.path.exists(pathm.to_sys(path))

    def set_modified(self, path, new_modified, *args, **kwargs):
        new_modified = utc_to_local(new_modified)
        os.utime(pathm.to_sys(path), (new_modified, new_modified))

    if supports_chmod:
        def chmod(self, path, mode, *args, **kwargs):
            if mode is None:
                return

            os.chmod(path, mode)

    def create_symlink(self, path, link_path, *args, **kwargs):
        os.symlink(pathm.to_sys(link_path), pathm.to_sys(path))
