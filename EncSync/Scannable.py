#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import ctypes
import sys
import time
from datetime import datetime
from . import Paths
from .Encryption import pad_size, MIN_ENC_SIZE
from .Node import normalize_node
from .YandexDiskApi import parse_date
from .YandexDiskApi.Exceptions import UnknownYandexDiskError
from . import PathMatch

if sys.platform.startswith("win"):
    def is_reparse_point(path):
        # https://stackoverflow.com/questions/15258506/os-path-islink-on-windows-with-python
        FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
        return bool(os.path.isdir(path) and (ctypes.windll.kernel32.GetFileAttributesW(path) & FILE_ATTRIBUTE_REPARSE_POINT))
else:
    def is_reparse_point(path):
        return False

class BaseScannable(object):
    def __init__(self, path=None, type=None, modified=0, size=0):
        self.path = path
        self.type = type
        self.modified = modified
        self.size = size

    def identify(self):
        raise NotImplementedError

    def listdir(self, allowed_paths=None):
        raise NotImplementedError

    def to_node(self):
        raise NotImplementedError

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.path)

    def scan(self, allowed_paths=None, *sort_args, **sort_kwargs):
        if allowed_paths is None:
            allowed_paths = []

        if self.type is None:
            self.identify()

        res = {"f": [], "d": []}

        if self.type != "d":
            return res

        content = list(self.listdir(allowed_paths))

        for i in content:
            if i.type is None:
                i.identify()

        sort_kwargs.setdefault("key", lambda x: x.path)
        content.sort(*sort_args, **sort_kwargs)

        for i in content:
            if i.type in ("f", "d"):
                res[i.type].append(i)

        return res

    def full_scan(self, allowed_paths=None):
        if allowed_paths is None:
            allowed_paths = []

        if not PathMatch.match(self.path, allowed_paths):
            return

        flist = self.scan(allowed_paths)
        flist["d"].reverse()

        while True:
            for s in flist["f"][::-1]:
                yield s

            flist["f"].clear()

            if len(flist["d"]) == 0:
                break

            s = flist["d"].pop()

            yield s

            scan_result = s.scan(allowed_paths)
            scan_result["d"].reverse()

            flist["f"] = scan_result["f"]
            flist["d"] += scan_result["d"]
            del scan_result

class LocalScannable(BaseScannable):
    def identify(self):
        self.path = os.path.abspath(self.path)
        self.path = os.path.expanduser(self.path)

        if is_reparse_point(self.path):
            self.type = None
            return

        if os.path.isfile(self.path):
            self.type = "f"
        elif os.path.isdir(self.path):
            self.type = "d"
        else:
            self.type = None
            return

        if self.type == "f":
            self.size = pad_size(os.path.getsize(self.path))
        else:
            self.size = 0

        m = os.path.getmtime(self.path)

        try:
            self.modified = datetime.utcfromtimestamp(m).timestamp()
        except (OverflowError, OSError):
            self.modified = 0

    def listdir(self, allowed_paths=None):
        if allowed_paths is None:
            allowed_paths = []

        for i in os.listdir(self.path):
            path = os.path.join(self.path, i)
            path_norm = Paths.from_sys(path)
            if os.path.isdir(path):
                path_norm = Paths.dir_normalize(path_norm)

            if PathMatch.match(path_norm, allowed_paths):
                yield LocalScannable(path)

    def to_node(self):
        node = {"type": self.type,
                "path": self.path,
                "modified": self.modified,
                "padded_size": self.size,
                "IVs": b""}
        normalize_node(node)

        return node

class RemoteScannable(BaseScannable):
    def __init__(self, encsync, prefix, data=None):
        if data is not None:
            path = data["path"]
            enc_path = data["enc_path"]
            type = data["type"][0]

            modified = data["modified"]
            modified = time.mktime(parse_date(modified))

            size = max(data["size"] - MIN_ENC_SIZE, 0)

            IVs = data["IVs"]
        else:
            path = prefix
            enc_path = prefix
            type = "d"
            modified = None
            size = 0
            IVs = b""

        BaseScannable.__init__(self, path, type, modified, size)
        self.enc_path = enc_path
        self.IVs = IVs
        self.prefix = prefix

        self.encsync = encsync
        self.ynd = encsync.ynd

    def identify(self):
        response = self.ynd.get_meta(self.enc_path, max_retries=30)

        if not response["success"]:
            raise Exception()

        data = response["data"]

        modified = data["modified"]
        modified = time.mktime(parse_date(modified))

        self.modified = modified

        self.size = data.get("size", 0)
        self.type = data["type"][0]

    def listdir(self, allowed_paths=None):
        if allowed_paths is None:
            allowed_paths = []

        dirs = []
        for j in range(10):
            try:
                for i in self.ynd.ls(self.enc_path):
                    data = i["data"]
                    enc_path = Paths.join(self.enc_path, data["name"])
                    path, IVs = self.encsync.decrypt_path(enc_path, self.prefix)

                    if not PathMatch.match(path, allowed_paths):
                        continue

                    dirs.append({"path": path,
                                 "enc_path": enc_path,
                                 "type": data["type"],
                                 "modified": data["modified"],
                                 "size": data.get("size", 0),
                                 "IVs": IVs})
                break
            except UnknownYandexDiskError as e:
                dirs.clear()
                if j == 9:
                    raise e

        for i in dirs:
            yield RemoteScannable(self.encsync, self.prefix, i)

    def to_node(self):
        node = {"type": self.type,
                "path": self.path,
                "modified": self.modified,
                "padded_size": self.size,
                "IVs": self.IVs}
        normalize_node(node)

        return node

def scan_files(scannable, allowed_paths=None):
    if allowed_paths is None:
        allowed_paths = []

    for i in scannable.full_scan(allowed_paths):
        yield (i, i.to_node())
