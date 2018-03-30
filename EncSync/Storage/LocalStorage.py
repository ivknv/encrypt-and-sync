# -*- coding: utf-8 -*-

import os
import shutil
import stat
import time

from .. import Paths
from ..common import is_windows, get_file_size

from .Storage import Storage
from .Exceptions import ControllerInterrupt
from .DownloadController import DownloadController
from .UploadController import UploadController

__all__ = ["LocalStorage"]

MIN_READ_SIZE = 4 * 1024**2 # Bytes

if is_windows():
    def _is_reparse_point(stat_result):
        return stat_result.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
else:
    def _is_reparse_point(stat_result):
        return False

class LocalDownloadController(DownloadController):
    def __init__(self, in_path, out_file):
        DownloadController.__init__(self, out_file)

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
    def __init__(self, in_file, out_path):
        UploadController.__init__(self, in_file)

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

    def get_meta(self, path, *args, **kwargs):
        path = Paths.to_sys(path)
        filename = os.path.split(path)[1]

        s = os.lstat(path)
        real_path = None

        if stat.S_ISREG(s.st_mode):
            resource_type = "file"
            size = s.st_size

            try:
                modified = time.mktime(time.gmtime(s.st_mtime))
                modified = max(modified, 0)
            except (OSError, OverflowError):
                modified = 0
        elif stat.S_ISDIR(s.st_mode):
            if _is_reparse_point(s):
                return {"type":     None,
                        "name":     filename,
                        "modified": 0,
                        "size":     0,
                        "link":     real_path}

            if stat.S_ISLNK(s.st_mode):
                s = os.stat(path)
                real_path = Paths.from_sys(os.path.realpath(path))

            resource_type = "dir"
            size = 0
            modified = 0
        else:
            return {"type":     None,
                    "name":     filename,
                    "modified": 0,
                    "size":     0,
                    "link":     real_path}

        return {"type":     resource_type,
                "name":     filename,
                "modified": modified,
                "size":     size,
                "link":     real_path}

    def listdir(self, path, *args, **kwargs):
        for entry in os.scandir(Paths.to_sys(path)):
            real_path = None
            
            if entry.is_file():
                resource_type = "file"
                size = entry.stat().st_size

                try:
                    modified = time.mktime(time.gmtime(entry.stat().st_mtime))
                    modified = max(modified, 0)
                except (OSError, OverflowError):
                    modified = 0
            elif entry.is_dir():
                if _is_reparse_point(entry.stat()):
                    continue

                if entry.is_symlink():
                    real_path = Paths.from_sys(os.path.realpath(entry.path))

                resource_type = "dir"
                size = 0
                modified = 0
            else:
                continue

            yield {"type":     resource_type,
                   "name":     entry.name,
                   "modified": modified,
                   "size":     size,
                   "link":     real_path}

    def mkdir(self, path, *args, **kwargs):
        os.mkdir(Paths.to_sys(path))

    def remove(self, path, *args, **kwargs):
        path = Paths.to_sys(path)

        try:
            shutil.rmtree(path)
        except NotADirectoryError:
            # os.remove() raises PermissionError when path is a directory
            os.remove(path)

    def upload(self, in_file, out_path, *args, **kwargs):
        out_path = Paths.to_sys(out_path)

        controller = LocalUploadController(in_file, out_path)

        return controller

    def download(self, in_path, out_file, *args, **kwargs):
        in_path = Paths.to_sys(in_path)

        controller = LocalDownloadController(in_path, out_file)

        return controller

    def is_file(self, path, *args, **kwargs):
        return os.path.isfile(Paths.to_sys(path))

    def is_dir(self, path, *args, **kwargs):
        return os.path.isdir(Paths.to_sys(path))

    def exists(self, path, *args, **kwargs):
        return os.path.exists(Paths.to_sys(path))
