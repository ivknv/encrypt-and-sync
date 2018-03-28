# -*- coding: utf-8 -*-

from .. import Paths

from .FolderStorage import FolderStorage

__all__ = ["LocalFolderStorage"]

class LocalFolderStorage(FolderStorage):
    def get_file(self, path):
        path = Paths.join(self.prefix, path)

        if self.encrypted:
            path = Paths.to_sys(self.encrypt_path(path)[0])

            yield None
            yield self.config.temp_decrypt(path)
        else:
            yield None
            yield open(Paths.to_sys(path), "rb")

    def get_encrypted_file(self, path):
        path = Paths.join(self.prefix, path)

        if self.encrypted:
            path = Paths.to_sys(self.encrypt_path(path)[0])

            yield None
            yield open(path, "rb")
        else:
            yield None
            yield self.config.temp_encrypt(Paths.to_sys(path))
