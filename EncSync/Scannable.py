#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import ctypes
import sys
from datetime import datetime

import requests.exceptions
from yadisk.exceptions import UnknownYaDiskError

from . import Paths
from .Encryption import pad_size, MIN_ENC_SIZE
from .common import normalize_node
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
    def __init__(self, encsync, prefix, enc_path=None, resource=None):
        if resource is not None:
            type = resource.type[0]

            modified = resource.modified.timestamp()

            size = max((resource.size or 0) - MIN_ENC_SIZE, 0)
        else:
            if enc_path is None:
                enc_path = prefix

            type = "d"
            modified = None
            size = 0

        path, IVs = encsync.decrypt_path(enc_path, prefix)

        BaseScannable.__init__(self, path, type, modified, size)
        self.enc_path = enc_path
        self.IVs = IVs
        self.prefix = prefix

        self.encsync = encsync
        self.ynd = encsync.ynd

    def identify(self):
        resource = self.ynd.get_meta(self.enc_path, n_retries=30)

        self.modified = resource.modified.timestamp() - resource.modified.utcoffset().seconds

        self.size = resource.size or 0
        self.type = resource.type[0]

    def listdir(self, allowed_paths=None):
        if allowed_paths is None:
            allowed_paths = []

        scannables = []

        for j in range(10):
            try:
                for resource in self.ynd.listdir(self.enc_path):
                    enc_path = Paths.join(self.enc_path, resource.name)

                    scannable = RemoteScannable(self.encsync, self.prefix, enc_path, resource)

                    path = scannable.path

                    if scannable.type == "d":
                        path = Paths.dir_normalize(path)

                    if PathMatch.match(path, allowed_paths):
                        scannables.append(scannable)
                break
            except (UnknownYaDiskError, requests.exceptions.RequestException) as e:
                scannables.clear()
                if j == 9:
                    raise e

        for i in scannables:
            yield i

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
