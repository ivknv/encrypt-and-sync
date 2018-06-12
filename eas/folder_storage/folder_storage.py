# -*- coding: utf-8 -*-

from ..filelist import FileList
from .. import encryption
from .. import pathm

__all__ = ["FolderStorage"]

class FolderStorage(object):
    """
        Implements functionality necessary for the synchronizer (file access and encryption).

        :param folder_name: `str`, name of the folder
        :param config: an instance of `config`
        :param directory: `str`, path to the directory with databases

        :ivar config: an instance of `Config`
        :ivar folder: `dict`, folder information
        :ivar encrypted: `bool`, tells whether the folder is encrypted or not
        :ivar storage: an instance of `Storage`
        :ivar prefix: `str`, directory root
        :ivar filename_encoding: `str`, filename encoding to use
    """

    def __init__(self, folder_name, config, directory=None, filelist=None):
        self.config = config
        self.folder = config.folders[folder_name]
        self.encrypted = self.folder["encrypted"]
        self.storage = config.storages[self.folder["type"]]
        self.prefix = pathm.dir_normalize(self.folder["path"])
        self.filename_encoding = self.folder["filename_encoding"]

        if filelist is None:
            self.filelist = FileList(folder_name, directory)
        else:
            self.filelist = filelist

        self.filelist.create()

    def get_ivs(self, full_path):
        node = self.filelist.find_node(full_path)

        if node["IVs"] is not None:
            return node["IVs"]

        parent = pathm.dir_normalize(pathm.split(full_path)[0])

        if parent == self.prefix:
            return b""

        node = self.filelist.find_node(parent)

        if node["IVs"] is not None:
            return node["IVs"] + encryption.gen_IV()

        return b""

    def encrypt_path(self, full_path, ivs=None):
        """
            Encrypt a path with existing IVs.

            :param path: `str`, path to encrypt
            :param ivs: `bytes` or `None`, IVs to encrypt with, will be looked up if `None`

            :returns: a `tuple` of encrypted path (`str`) and IVs (`bytes`)
        """

        full_path = pathm.join_properly("/", full_path)

        if ivs is None:
            ivs = self.get_ivs(full_path)

        return self.config.encrypt_path(full_path, self.prefix, ivs, self.filename_encoding)

    def get_file(self, path, *args, ivs=None, **kwargs):
        """
            Get a file-like object at `path`.

            :param path: `str`, unencrypted path to the file
            :param ivs: `bytes` or `None`, IVs to encrypt with, will be looked up if `None`

            :returns: file-like object with unencrypted contents
        """

        raise NotImplementedError

    def get_encrypted_file(self, path, *args, ivs=None, **kwargs):
        """
            Get an encrypted file-like object at `path`.

            :param path: `str`, unencrypted path to the file
            :param ivs: `bytes` or `None`, IVs to encrypt with, will be looked up if `None`

            :returns: file-like object with encrypted contents
        """

        raise NotImplementedError

    def get_meta(self, path, *args, ivs=None, **kwargs):
        path = pathm.join(self.prefix, path)

        if self.encrypted:
            path, ivs = self.encrypt_path(path, ivs)

        meta = self.storage.get_meta(path, *args, **kwargs)

        if self.encrypted:
            if pathm.dir_normalize(path) != self.prefix:
                meta["name"] = self.config.decrypt_path(
                    meta["name"],
                    filename_encoding=self.filename_encoding)[0]

        return meta

    def listdir(self, path, *args, ivs=None, **kwargs):
        path = pathm.join(self.prefix, path)

        if self.encrypted:
            path, ivs = self.encrypt_path(path, ivs)

        result = self.storage.listdir(path, *args, **kwargs)

        if self.encrypted:
            for meta in result:
                meta["name"] = self.config.decrypt_path(meta["name"],
                                                        filename_encoding=self.filename_encoding)[0]

                yield meta
        else:
            yield from result

    def mkdir(self, path, *args, ivs=None, **kwargs):
        path = pathm.join(self.prefix, path)

        if self.encrypted:
            path, ivs = self.encrypt_path(path, ivs)

        self.storage.mkdir(path, *args, **kwargs)

        return ivs or b""

    def upload(self, in_file, out_path, *args, ivs=None, **kwargs):
        out_path = pathm.join(self.prefix, out_path)

        if self.encrypted:
            out_path, ivs = self.encrypt_path(out_path, ivs)

        return self.storage.upload(in_file, out_path, *args, **kwargs), ivs or b""

    def exists(self, path, *args, ivs=None, **kwargs):
        path = pathm.join(self.prefix, path)

        if self.encrypted:
            path, ivs = self.encrypt_path(path, ivs)

        return self.storage.exists(path, *args, **kwargs)

    def remove(self, path, *args, ivs=None, **kwargs):
        path = pathm.join(self.prefix, path)

        if self.encrypted:
            path, ivs = self.encrypt_path(path, ivs)

        return self.storage.remove(path, *args, **kwargs)

    def set_modified(self, path, new_modified, *args, ivs=None, **kwargs):
        path = pathm.join(self.prefix, path)

        if self.encrypted:
            path, ivs = self.encrypt_path(path, ivs)

        return self.storage.set_modified(path, new_modified, *args, **kwargs)
