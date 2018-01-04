# -*- coding: utf-8 -*-

from .. import Paths

from .TargetStorage import TargetStorage

__all__ = ["LocalTargetStorage"]

class LocalTargetStorage(TargetStorage):
    def get_file(self, path):
        path = Paths.join(self.prefix, path)

        if self.encrypted:
            path = Paths.to_sys(self.encrypt_path(path))

            yield None
            yield self.encsync.temp_decrypt(path)
        else:
            yield None
            yield open(Paths.to_sys(path), "rb")

    def get_encrypted_file(self, path):
        path = Paths.join(self.prefix, path)

        if self.encrypted:
            path = Paths.to_sys(self.encrypt_path(path))

            yield None
            yield open(path, "rb")
        else:
            yield None
            yield self.encsync.temp_encrypt(Paths.to_sys(path))
