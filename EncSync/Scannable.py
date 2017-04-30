#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
from datetime import datetime
from . import paths
from .Encryption import pad_size, MIN_ENC_SIZE
from .Node import normalize_node
from .YandexDiskApi import parse_date

class BaseScannable(object):
    def __init__(self, path=None, type=None, modified=0, size=0):
        self.path = path
        self.type = type
        self.modified = modified
        self.size = size

    def identify(self):
        raise NotImplementedError

    def listdir(self):
        raise NotImplementedError

    def to_node(self):
        raise NotImplementedError

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.path)

    def scan(self, *sort_args, **sort_kwargs):
        if self.type is None:
            self.identify()

        res = {"f": [], "d": []}

        if self.type != "d":
            return res

        content = list(self.listdir())

        for i in content:
            if i.type is None:
                i.identify()

        sort_kwargs.setdefault("key", lambda x: x.path)
        content.sort(*sort_args, **sort_kwargs)

        for i in content:
            if i.type in ("f", "d"):
                res[i.type].append(i)

        return res

    def full_scan(self):
        flist = self.scan()
        flist["d"].reverse()

        while True:
            for s in flist["f"][::-1]:
                yield s

            flist["f"].clear()

            if len(flist["d"]) == 0:
                break

            s = flist["d"].pop()

            yield s

            scan_result = s.scan()
            scan_result["d"].reverse()

            flist["f"] = scan_result["f"]
            flist["d"] += scan_result["d"]
            del scan_result

class LocalScannable(BaseScannable):
    def identify(self):
        self.path = os.path.abspath(self.path)
        self.path = os.path.expanduser(self.path)

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
        except OverflowError:
            self.modified = 0

    def listdir(self):
        for i in os.listdir(self.path):
            yield LocalScannable(os.path.join(self.path, i))

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

    def listdir(self):
        dirs = []
        for j in range(10):
            try:
                for i in self.ynd.ls(self.enc_path):
                    data = i["data"]
                    enc_path = paths.join(self.enc_path, data["name"])
                    path, IVs = self.encsync.decrypt_path(enc_path, self.prefix)

                    dirs.append({"path": path,
                                 "enc_path": enc_path,
                                 "type": data["type"],
                                 "modified": data["modified"],
                                 "size": data.get("size", 0),
                                 "IVs": IVs})
                break
            except Exception as e:
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

def scan_files(scannable):
    for i in scannable.full_scan():
        yield (i, i.to_node())
