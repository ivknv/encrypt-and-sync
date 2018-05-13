#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import Paths
from .encryption import pad_size, MIN_ENC_SIZE
from .common import normalize_node, DummyException
from .storage.exceptions import TemporaryStorageError
from . import path_match

__all__ = ["BaseScannable", "DecryptedScannable", "EncryptedScannable",
           "scan_files"]

try:
    from yadisk.exceptions import UnauthorizedError
except ImportError:
    UnauthorizedError = DummyException

class BaseScannable(object):
    def __init__(self, storage, path=None, type=None, modified=0, size=0):
        self.storage = storage
        self.path = path
        self.type = type
        self.modified = modified
        self.size = size

    def identify(self, ignore_unreachable=False):
        raise NotImplementedError

    def listdir(self, allowed_paths=None, ignore_unreachable=False):
        raise NotImplementedError

    def to_node(self):
        node = {"type": self.type,
                "path": self.path,
                "modified": self.modified,
                "padded_size": self.size,
                "IVs": b""}

        normalize_node(node)

        return node

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.path)

    def scan(self, allowed_paths=None, ignore_unreachable=False, **sort_kwargs):
        if allowed_paths is None:
            allowed_paths = []

        if self.type is None:
            self.identify(ignore_unreachable)

        res = {"f": [], "d": []}

        if self.type != "d":
            return res

        content = list(self.listdir(allowed_paths,
                                    ignore_unreachable=ignore_unreachable))

        for i in content:
            if i.type is None:
                try:
                    i.identify(ignore_unreachable)
                except FileNotFoundError:
                    i.type = None

        sort_kwargs.setdefault("key", lambda x: x.path)
        content.sort(**sort_kwargs)

        for i in content:
            if i.type in ("f", "d"):
                res[i.type].append(i)

        return res

    def full_scan(self, allowed_paths=None, ignore_unreachable=False):
        if allowed_paths is None:
            allowed_paths = []

        if not path_match.match(self.path, allowed_paths):
            return

        flist = self.scan(allowed_paths, ignore_unreachable=ignore_unreachable)
        flist["d"].reverse()

        while True:
            for s in flist["f"][::-1]:
                yield s

            flist["f"].clear()

            if len(flist["d"]) == 0:
                break

            s = flist["d"].pop()

            yield s

            try:
                scan_result = s.scan(allowed_paths, ignore_unreachable=ignore_unreachable)
            except FileNotFoundError:
                continue

            scan_result["d"].reverse()

            flist["f"] = scan_result["f"]
            flist["d"] += scan_result["d"]
            del scan_result

class DecryptedScannable(BaseScannable):
    def identify(self, ignore_unreachable=False):
        self.path = Paths.join_properly("/", self.path)

        try:
            meta = self.storage.get_meta(self.path, n_retries=30)
        except (FileNotFoundError, PermissionError) as e:
            if ignore_unreachable:
                self.type = None
                return

            raise e

        if meta["type"] == "d":
            self.path = Paths.dir_normalize(self.path)
        elif not meta["type"]:
            self.type = None
            return

        self.type = meta["type"][0]
        self.modified = meta["modified"]
        self.size = meta["size"]

        if self.type == "f":
            self.size = pad_size(self.size)

    def listdir(self, allowed_paths=None, ignore_unreachable=False):
        if allowed_paths is None:
            allowed_paths = []

        scannables = []

        for i in range(10):
            scannables.clear()

            try:
                for meta in self.storage.listdir(self.path):
                    if meta["type"] is None:
                        continue

                    path = Paths.join(self.path, meta["name"])

                    if meta["type"] == "dir":
                        path = Paths.dir_normalize(path)

                        if meta["link"] is not None:
                            if Paths.contains(meta["link"], path):
                                continue

                    meta["size"] = pad_size(meta["size"])

                    if path_match.match(path, allowed_paths):
                        s = DecryptedScannable(self.storage, path, meta["type"][0],
                                               meta["modified"], meta["size"])
                        scannables.append(s)
                break
            except (TemporaryStorageError, UnauthorizedError) as e:
                # Yandex.Disk seems to randomly throw UnauthorizedError sometimes
                if i == 9:
                    raise e
            except (FileNotFoundError, PermissionError) as e:
                if ignore_unreachable:
                    return []

                raise e

        return scannables

class EncryptedScannable(BaseScannable):
    def __init__(self, storage, prefix, enc_path=None, type=None, modified=0, size=0,
                 filename_encoding="base64"):

        if enc_path is None:
            enc_path = prefix

        path, IVs = storage.config.decrypt_path(enc_path, prefix,
                                                 filename_encoding=filename_encoding)
        
        BaseScannable.__init__(self, storage, path, type, modified, size)

        self.prefix = prefix
        self.enc_path = enc_path
        self.IVs = IVs
        self.filename_encoding = filename_encoding

    def to_node(self):
        node = BaseScannable.to_node(self)
        node["IVs"] = self.IVs

        return node

    def identify(self, ignore_unreachable=False):
        self.enc_path = Paths.join_properly("/", self.enc_path)

        try:
            meta = self.storage.get_meta(self.enc_path, n_retries=30)
        except (FileNotFoundError, PermissionError) as e:
            if ignore_unreachable:
                self.type = None
                return

            raise e

        if meta["type"] == "d":
            self.enc_path = Paths.dir_normalize(self.enc_path)
            self.path = Paths.dir_normalize(self.path)
        elif not meta["type"]:
            self.type = None
            return

        self.type = meta["type"][0]
        self.modified = meta["modified"]
        self.size = meta["size"]

        self.size = max((self.size or 0) - MIN_ENC_SIZE, 0)

    def listdir(self, allowed_paths=None, ignore_unreachable=False):
        if allowed_paths is None:
            allowed_paths = []

        scannables = []

        for i in range(10):
            scannables.clear()

            try:
                for meta in self.storage.listdir(self.enc_path):
                    if meta["type"] is None:
                        continue

                    enc_path = Paths.join(self.enc_path, meta["name"])

                    if meta["type"] == "dir":
                        enc_path = Paths.dir_normalize(enc_path)

                        if meta["link"] is not None:
                            if Paths.contains(meta["link"], enc_path):
                                continue

                    meta["size"] = max((meta["size"] or 0) - MIN_ENC_SIZE, 0)

                    scannable = EncryptedScannable(self.storage, self.prefix, enc_path,
                                                   meta["type"][0], meta["modified"], meta["size"],
                                                   filename_encoding=self.filename_encoding)

                    if path_match.match(scannable.path, allowed_paths):
                        scannables.append(scannable)
                break
            except (TemporaryStorageError, UnauthorizedError) as e:
                # Yandex.Disk seems to randomly throw UnauthorizedError sometimes
                if i == 9:
                    raise e
            except (FileNotFoundError, PermissionError) as e:
                if ignore_unreachable:
                    return []

                raise e

        return scannables

def scan_files(scannable, allowed_paths=None, ignore_unreachable=False):
    if allowed_paths is None:
        allowed_paths = []

    for i in scannable.full_scan(allowed_paths, ignore_unreachable=ignore_unreachable):
        yield (i, i.to_node())
