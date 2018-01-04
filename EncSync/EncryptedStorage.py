# -*- coding: utf-8 -*-

import tempfile

from . import Paths
from .Storage import get_storage
from .TargetStorage import get_target_storage

__all__ = ["EncryptedStorage"]

class EncryptedStorage(object):
    def __init__(self, encsync, storage_name, directory=None):
        self.encsync = encsync
        self.name = storage_name
        self.directory = directory
        self.target_storage_class = get_target_storage(storage_name)
        self.storage = get_storage(storage_name)(self.encsync)
        self.target_storages = {}

    def get_target_storage(self, target_name, dirname):
        try:
            return self.target_storages[(target_name, dirname)]
        except KeyError:
            target_storage = self.target_storage_class(target_name,
                                                       dirname,
                                                       self.encsync,
                                                       self.directory)
            self.target_storages[(target_name, dirname)] = target_storage

            return target_storage

    def is_encrypted(self, path):
        target, dirname = self.identify_directory(path)

        if target is None:
            return False

        return target[dirname]["encrypted"]

    def identify_directory(self, path):
        path = Paths.join_properly("/", path)
        best_match, best_dir = self.encsync.identify_target(self.name, path)

        if best_dir is None or not best_match[best_dir]["encrypted"]:
            return None, None

        return best_match, best_dir

    def get_meta(self, path, *args, **kwargs):
        target, dirname = self.identify_directory(path)

        if target is None:
            return self.storage.get_meta(path, *args, **kwargs)

        target_storage = self.get_target_storage(target["name"], dirname)
        path = Paths.cut_prefix(path, target_storage.prefix)

        return target_storage.get_meta(path, *args, **kwargs)

    def mkdir(self, path, *args, **kwargs):
        target, dirname = self.identify_directory(path)

        if target is None:
            return self.storage.mkdir(path, *args, **kwargs), b""

        target_storage = self.get_target_storage(target["name"], dirname)
        path = Paths.cut_prefix(path, target_storage.prefix)

        return target_storage.mkdir(path, *args, **kwargs)

    def upload(self, in_file, out_path, *args, **kwargs):
        target, dirname = self.identify_directory(out_path)

        if target is None:
            return self.storage.upload(in_file, out_path, *args, **kwargs), b""

        target_storage = self.get_target_storage(target["name"], dirname)
        out_path = Paths.cut_prefix(out_path, target_storage.prefix)

        return target_storage.upload(in_file, out_path, *args, **kwargs)

    def get_file(self, path):
        target, dirname = self.identify_directory(path)

        if target is None:
            if self.storage.name == "local":
                yield None
                yield open(Paths.to_sys(path), "rb")
            else:
                tmp_file = tempfile.TemporaryFile("w+b")
                controller = self.storage.download(path, tmp_file)
                yield controller

                controller.work()

                tmp_file.seek(0)
                yield tmp_file

            return

        target_storage = self.get_target_storage(target["name"], dirname)
        path = Paths.cut_prefix(path, target_storage.prefix)

        yield from target_storage.get_file(path)

    def get_encrypted_file(self, path):
        target, dirname = self.identify_directory(path)

        if target is None:
            if self.storage.name == "local":
                yield None
                yield self.encsync.temp_encrypt(Paths.to_sys(path))
            else:
                tmp_file = tempfile.TemporaryFile("w+b")
                controller = self.storage.download(path, tmp_file)
                yield controller

                controller.work()

                yield self.encsync.temp_encrypt(tmp_file)

            return

        target_storage = self.get_target_storage(target["name"], dirname)
        path = Paths.cut_prefix(path, target_storage.prefix)

        yield from target_storage.get_encrypted_file(path)

    def is_dir(self, path, *args, **kwargs):
        target, dirname = self.identify_directory(path)

        if target is None:
            return self.storage.is_dir(path, *args, **kwargs)

        target_storage = self.get_target_storage(target["name"], dirname)
        path = Paths.cut_prefix(path, target_storage.prefix)

        return target_storage.is_dir(path, *args, **kwargs)

    def listdir(self, path, *args, **kwargs):
        target, dirname = self.identify_directory(path)

        if target is None:
            return self.storage.listdir(path, *args, **kwargs)

        target_storage = self.get_target_storage(target["name"], dirname)
        path = Paths.cut_prefix(path, target_storage.prefix)

        return target_storage.listdir(path, *args, **kwargs)
