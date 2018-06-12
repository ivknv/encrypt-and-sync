# -*- coding: utf-8 -*-

from .. import pathm

from .folder_storage import FolderStorage

__all__ = ["LocalFolderStorage"]

class LocalFolderStorage(FolderStorage):
    def get_file(self, path, *args, ivs=None, **kwargs):
        path = pathm.join(self.prefix, path)

        if self.encrypted:
            path = pathm.to_sys(self.encrypt_path(path, ivs)[0])

            yield None
            yield self.config.temp_decrypt(path)
        else:
            yield None
            yield open(pathm.to_sys(path), "rb")

    def get_encrypted_file(self, path, *args, ivs=None, **kwargs):
        path = pathm.join(self.prefix, path)

        if self.encrypted:
            path = pathm.to_sys(self.encrypt_path(path, ivs)[0])

            yield None
            yield open(path, "rb")
        else:
            yield None
            yield self.config.temp_encrypt(pathm.to_sys(path))
