# -*- coding: utf-8 -*-

import tempfile

from . import pathm
from .storage import Storage
from .folder_storage import get_folder_storage

__all__ = ["EncryptedStorage"]

class EncryptedStorage(object):
    def __init__(self, config, storage_name, directory=None):
        self.config = config
        self.name = storage_name
        self.directory = directory
        self.folder_storage_class = get_folder_storage(storage_name)
        self.storage = Storage.get_storage(storage_name)(self.config)
        self.folder_storages = {}

    def get_folder_storage(self, folder_name):
        try:
            return self.folder_storages[folder_name]
        except KeyError:
            folder_storage = self.folder_storage_class(folder_name,
                                                       self.config,
                                                       self.directory)
            self.folder_storages[folder_name] = folder_storage

            return folder_storage

    def is_encrypted(self, path):
        folder = self.identify_folder(path)

        if folder is None:
            return False

        return folder["encrypted"]

    def identify_folder(self, path):
        path = pathm.join_properly("/", path)
        best_match = self.config.identify_folder(self.name, path)

        if best_match is None or not best_match["encrypted"]:
            return None

        return best_match

    def get_meta(self, path, *args, **kwargs):
        folder = self.identify_folder(path)

        if folder is None:
            return self.storage.get_meta(path, *args, **kwargs)

        folder_storage = self.get_folder_storage(folder["name"])
        path = pathm.cut_prefix(path, folder_storage.prefix)

        return folder_storage.get_meta(path, *args, **kwargs)

    def mkdir(self, path, *args, **kwargs):
        folder = self.identify_folder(path)

        if folder is None:
            return self.storage.mkdir(path, *args, **kwargs), b""

        folder_storage = self.get_folder_storage(folder["name"])
        path = pathm.cut_prefix(path, folder_storage.prefix)

        return folder_storage.mkdir(path, *args, **kwargs)

    def upload(self, in_file, out_path, *args, **kwargs):
        folder = self.identify_folder(out_path)

        if folder is None:
            return self.storage.upload(in_file, out_path, *args, **kwargs), b""

        folder_storage = self.get_folder_storage(folder["name"])
        out_path = pathm.cut_prefix(out_path, folder_storage.prefix)

        return folder_storage.upload(in_file, out_path, *args, **kwargs)

    def get_file(self, path, ivs=None):
        folder = self.identify_folder(path)

        if folder is None:
            if self.storage.name == "local":
                yield None
                yield open(pathm.to_sys(path), "rb")
            else:
                tmp_file = tempfile.TemporaryFile("w+b", dir=self.config.temp_dir)
                task = self.storage.download(path, tmp_file)
                yield task

                task.run()

                tmp_file.seek(0)
                yield tmp_file

            return

        folder_storage = self.get_folder_storage(folder["name"])
        path = pathm.cut_prefix(path, folder_storage.prefix)

        yield from folder_storage.get_file(path, ivs=ivs)

    def get_encrypted_file(self, path, ivs=None):
        folder = self.identify_folder(path)

        if folder is None:
            if self.storage.name == "local":
                yield None
                yield self.config.temp_encrypt(pathm.to_sys(path))
            else:
                tmp_file = tempfile.TemporaryFile("w+b", dir=self.config.temp_dir)
                task = self.storage.download(path, tmp_file)
                yield task

                task.work()

                yield self.config.temp_encrypt(tmp_file)

            return

        folder_storage = self.get_folder_storage(folder["name"])
        path = pathm.cut_prefix(path, folder_storage.prefix)

        yield from folder_storage.get_encrypted_file(path, ivs=ivs)

    def is_dir(self, path, *args, **kwargs):
        folder = self.identify_folder(path)

        if folder is None:
            return self.storage.is_dir(path, *args, **kwargs)

        folder_storage = self.get_folder_storage(folder["name"])
        path = pathm.cut_prefix(path, folder_storage.prefix)

        return folder_storage.is_dir(path, *args, **kwargs)

    def listdir(self, path, *args, **kwargs):
        folder = self.identify_folder(path)

        if folder is None:
            return self.storage.listdir(path, *args, **kwargs)

        folder_storage = self.get_folder_storage(folder["name"])
        path = pathm.cut_prefix(path, folder_storage.prefix)

        return folder_storage.listdir(path, *args, **kwargs)
