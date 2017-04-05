#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import paths
from . import Encryption
import os

class EncPath(object):
    def __init__(self, encsync, path=None):
        self.encsync = encsync
        self._path = None
        self._path_enc = None
        self._local = None
        self._remote = None
        self._remote_enc = None
        self._local_prefix = None
        self._remote_prefix = None
        self._IVs = None

        self.path = path

    def copy(self):
        copy = EncPath(self.encsync, self.path)
        copy._IVs = self._IVs
        copy._local_prefix = self._local_prefix
        copy._remote_prefix = self._remote_prefix

        return copy

    def get_path(self):
        if None not in {self._local_prefix, self._local}:
            return paths.cut_prefix(self._local, self._local_prefix, sep=os.path.sep)
        elif self._remote_prefix is not None:
            if self._remote is not None:
                return paths.cut_prefix(self._remote, self._remote_prefix)
            elif self._remote_enc is not None:
                return paths.cut_prefix(self._remote_enc, self._remote_prefix)

        if self._path_enc is not None:
            if self._IVs is None or self._IVs == b"":
                path, self._IVs = self.encsync.decrypt_path(self._path_enc)
            else:
                path = self.encsync.decrypt_path(self._path_enc, IVs=self._IVs)

            return path

    def get_path_enc(self):
        if self.path is None:
            return

        self.update_IVs()

        if self._IVs is None or self._IVs == b"":
            path_enc, self._IVs = self.encsync.encrypt_path(self.path, IVs=b"")
        else:
            path_enc = self.encsync.encrypt_path(self.path, IVs=self._IVs)[0]

        return path_enc

    def get_local(self):
        prefix = self.local_prefix
        path = self.path
        if None not in {prefix, path}:
            return os.path.join(prefix, paths.to_sys(path))

    def get_remote(self):
        prefix = self.remote_prefix
        path = self.path
        if None not in {prefix, path}:
            return paths.join(prefix, path)

    def get_local_prefix(self):
        if None not in {self.path, self.local}:
            return paths.to_sys(paths.cut_off(paths.from_sys(self.local), self.path))

    def get_remote_prefix(self):
        if None not in {self.path, self.remote}:
            return paths.cut_off(self.remote, self.path)
        elif None not in {self.path_enc, self.remote_enc}:
            return paths.cut_off(self.remote_enc, self.path_enc)

    def get_remote_enc(self):
        if None not in {self.remote_prefix, self.path_enc}:
            return paths.join(self.remote_prefix, self.path_enc)

    def get_IVs(self):
        if self.path_enc is None:
            return

        IVs = b""

        for path in (i for i in self.path_enc.split("/") if i):
            IVs += Encryption.get_filename_IV(path)

        return IVs

    @property
    def path(self):
        if self._path is None:
            self._path = self.get_path()
        return self._path

    def update_IVs(self):
        if self._IVs is not None or self._IVs == b"":
            if self._path is None:
                n_dirs = 0
            else:
                n_dirs = sum(1 for i in self._path.split("/") if i)
            n_IVs = len(self._IVs) // 16
            while n_IVs < n_dirs:
                self._IVs += Encryption.gen_IV()
                n_IVs += 1
            self._IVs = self._IVs[:16 * n_dirs]

    @path.setter
    def path(self, value):
        if value is not None:
            self._path = paths.from_sys(value)
            if self._path.startswith("/"):
                self._path = self._path[1:]
        else:
            self._path = None
        self._path_enc = None
        self._local = None
        self._remote = None
        self._remote_enc = None

    @property
    def path_enc(self):
        if self._path_enc is None:
            self._path_enc = self.get_path_enc()
        return self._path_enc

    @path_enc.setter
    def path_enc(self, value):
        self._path_enc = value
        self._path = None
        self._local = None
        self._remote = None
        self._remote_enc = None
        self._IVs = None

    @property
    def local(self):
        if self._local is None:
            self._local = self.get_local()
        return self._local

    @property
    def remote(self):
        if self._remote is None:
            self._remote = self.get_remote()
        return self._remote

    @property
    def remote_enc(self):
        if self._remote_enc is None:
            self._remote_enc = self.get_remote_enc()
        return self._remote_enc

    @property
    def local_prefix(self):
        return self._local_prefix

    @local_prefix.setter
    def local_prefix(self, value):
        self._local_prefix = value
        self._local = None

    @property
    def remote_prefix(self):
        return self._remote_prefix

    @remote_prefix.setter
    def remote_prefix(self, value):
        self._remote_prefix = value
        self._remote = None
        self._remote_enc = None

    @property
    def IVs(self):
        if self._IVs is None:
            self._IVs = self.get_IVs()
        return self._IVs

    @IVs.setter
    def IVs(self, value):
        self._IVs = value
        self._remote_enc = None
        self._path_enc = None
