#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import Paths
from . import Encryption
from .FileList import RemoteFileList

class EncPath(object):
    """
        Encrypted path class.

        :param encsync: `EncSync` object
        :param path: path relative to the prefixes
    """

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
        """
            Makes an exact copy of the path.

            :returns: `EncPath`
        """

        copy = EncPath(self.encsync, self.path)
        copy._IVs = self._IVs
        copy._local_prefix = self._local_prefix
        copy._remote_prefix = self._remote_prefix

        return copy

    def get_IVs_from_db(self, directory=None):
        """
            Get IVs from the remote filelist database.

            :param directory: directory containing the database

            :returns: `bytes`
        """

        rlist = RemoteFileList(directory)

        node = rlist.find_node(self.remote)

        return node["IVs"]

    def _get_path(self):
        if self._path_enc is not None:
            path, self._IVs = self.encsync.decrypt_path(self._path_enc)

            return path

    def _get_path_enc(self):
        if self.path is None:
            return

        self._update_IVs()

        return self.encsync.encrypt_path(self.path, IVs=self._IVs)[0]

    def _get_local(self):
        prefix = self._local_prefix
        path = self.path

        if None not in (prefix, path):
            return Paths.join(prefix, path)

    def _get_remote(self):
        prefix = self._remote_prefix
        path = self.path

        if None not in (prefix, path):
            return Paths.join(prefix, path)

    def _get_remote_enc(self):
        if None not in (self._remote_prefix, self.path_enc):
            return Paths.join(self._remote_prefix, self.path_enc)

    def _get_IVs(self):
        if self.path_enc is None:
            return

        IVs = b""

        for name in (i for i in self.path_enc.split("/") if i):
            IVs += Encryption.get_filename_IV(name)

        return IVs

    @property
    def path(self):
        """Path relative to the prefixes (assumes "/" as a separator)."""

        if self._path is None:
            self._path = self._get_path()

        return self._path

    def _update_IVs(self):
        if self._IVs is None:
            self._IVs = b""

        if self._path is None:
            return

        n_names = sum(1 for i in self._path.split("/") if i)
        n_IVs = len(self._IVs) // 16

        while n_IVs < n_names:
            self._IVs += Encryption.gen_IV()
            n_IVs += 1

        self._IVs = self._IVs[:16 * n_names]

    @path.setter
    def path(self, value):
        if value is not None:
            self._path = Paths.from_sys_sep(value)
            if self._path.startswith("/") and self._path != "/":
                self._path = self._path[1:]
        else:
            self._path = None
        self._path_enc = None
        self._local = None
        self._remote = None
        self._remote_enc = None

    @property
    def path_enc(self):
        """Encrypted path relative to the prefixes."""

        if self._path_enc is None:
            self._path_enc = self._get_path_enc()
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
        """Local path (read only)."""

        if self._local is None:
            self._local = self._get_local()

        return self._local

    @property
    def remote(self):
        """Remote path (read only)."""

        if self._remote is None:
            self._remote = self._get_remote()

        return self._remote

    @property
    def remote_enc(self):
        """Encrypted remote path (read only)."""

        if self._remote_enc is None:
            self._remote_enc = self._get_remote_enc()

        return self._remote_enc

    @property
    def local_prefix(self):
        """Local prefix."""

        return self._local_prefix

    @local_prefix.setter
    def local_prefix(self, value):
        self._local_prefix = value
        self._local = None

    @property
    def remote_prefix(self):
        """Remote prefix."""

        return self._remote_prefix

    @remote_prefix.setter
    def remote_prefix(self, value):
        self._remote_prefix = Paths.dir_normalize(value)
        self._remote = None
        self._remote_enc = None

    @property
    def IVs(self):
        """Initialization vectors (IVs) of the encrypted path."""

        if self._IVs is None:
            self._IVs = self._get_IVs()

        return self._IVs

    @IVs.setter
    def IVs(self, value):
        self._IVs = value
        self._remote_enc = None
        self._path_enc = None
