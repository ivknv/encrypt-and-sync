# -*- coding: utf-8 -*-

from ..FileList import FileList
from .. import Encryption
from .. import Paths

__all__ = ["TargetStorage"]

class TargetStorage(object):
    """
        Implements functionality necessary for the synchronizer (file access and encryption).

        :param target_name: `str`, name of the target
        :param dirname: `str`, directory name ("src" or "dst")
        :param config: an instance of `config`
        :param directory: `str`, path to the directory with databases

        :ivar config: an instance of `config`
        :ivar target: `dict`, target information
        :ivar encrypted: `bool`, tells whether the source is encrypted or not
        :ivar dirname: `str`, directory name ("src" or "dst")
        :ivar storage: an instance of `Storage`
        :ivar prefix: `str`, directory root
        :ivar filename_encoding: `str`, filename encoding to use
    """

    def __init__(self, target_name, dirname, config, directory=None, filelist=None):
        self.config = config
        self.target = config.targets[target_name]
        self.dirname = dirname
        self.encrypted = self.target[dirname]["encrypted"]
        self.storage = config.storages[self.target[dirname]["name"]]
        self.prefix = Paths.dir_normalize(self.target[dirname]["path"])
        self.filename_encoding = self.target[dirname]["filename_encoding"]

        if filelist is None:
            self.filelist = FileList(target_name, self.storage.name, directory)
        else:
            self.filelist = filelist

        self.filelist.create()

    def get_ivs(self, full_path):
        node = self.filelist.find_node(full_path)

        if node["IVs"] is not None:
            return node["IVs"]

        parent = Paths.dir_normalize(Paths.split(full_path)[0])

        if parent == self.prefix:
            return b""

        node = self.filelist.find_node(parent)

        if node["IVs"] is not None:
            return node["IVs"] + Encryption.gen_IV()

        return b""

    def encrypt_path(self, full_path, ivs=None):
        """
            Encrypt a path with existing IVs.

            :param path: `str`, path to encrypt
            :param IVs: `bytes` or `None`, IVs to encrypt with, will be looked up if `None`

            :returns: `str`
        """

        full_path = Paths.join_properly("/", full_path)

        if ivs is None:
            ivs = self.get_ivs(full_path)

        return self.config.encrypt_path(full_path, self.prefix, ivs, self.filename_encoding)

    def get_file(self, path):
        """
            Get a file-like object at `path`.

            :param path: `str`, unencrypted path to the file

            :returns: file-like object with unencrypted contents
        """

        raise NotImplementedError

    def get_encrypted_file(self, path):
        """
            Get an encrypted file-like object at `path`.

            :param path: `str`, unencrypted path to the file

            :returns: file-like object with encrypted contents
        """

        raise NotImplementedError

    def get_meta(self, path, *args, **kwargs):
        path = Paths.join(self.prefix, path)

        if self.encrypted:
            path, ivs = self.encrypt_path(path)

        meta = self.storage.get_meta(path, *args, **kwargs)

        if self.encrypted:
            if Paths.dir_normalize(path) != self.prefix:
                meta["name"] = self.config.decrypt_path(
                    meta["name"],
                    filename_encoding=self.filename_encoding)[0]

        return meta

    def listdir(self, path, *args, **kwargs):
        path = Paths.join(self.prefix, path)

        if self.encrypted:
            path, ivs = self.encrypt_path(path)

        result = self.storage.listdir(path, *args, **kwargs)

        if self.encrypted:
            for meta in result:
                meta["name"] = self.config.decrypt_path(meta["name"],
                                                        filename_encoding=self.filename_encoding)[0]

                yield meta
        else:
            yield from result

    def mkdir(self, path, *args, **kwargs):
        path = Paths.join(self.prefix, path)
        ivs = b""

        if self.encrypted:
            path, ivs = self.encrypt_path(path)

        self.storage.mkdir(path, *args, **kwargs)

        return ivs

    def upload(self, in_file, out_path, *args, **kwargs):
        out_path = Paths.join(self.prefix, out_path)
        ivs = b""

        if self.encrypted:
            out_path, ivs = self.encrypt_path(out_path)

        return self.storage.upload(in_file, out_path, *args, **kwargs), ivs

    def exists(self, path, *args, **kwargs):
        path = Paths.join(self.prefix, path)

        if self.encrypted:
            path, ivs = self.encrypt_path(path)

        return self.storage.exists(path, *args, **kwargs)

    def remove(self, path, *args, **kwargs):
        path = Paths.join(self.prefix, path)

        if self.encrypted:
            path, ivs = self.encrypt_path(path)

        return self.storage.remove(path, *args, **kwargs)
