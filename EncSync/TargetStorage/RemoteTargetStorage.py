# -*- coding: utf-8 -*-

import tempfile

from .. import Paths
from .TargetStorage import TargetStorage

__all__ = ["RemoteTargetStorage"]

class RemoteTargetStorage(TargetStorage):
    def get_file(self, path):
        path = Paths.join(self.prefix, path)

        if self.encrypted:
            path = self.encrypt_path(path)

            with tempfile.TemporaryFile("w+b") as tmp_file:
                controller = self.storage.download(path, tmp_file)
                yield controller

                controller.work()

                tmp_file.seek(0)

                result = self.config.temp_decrypt(tmp_file)

            yield result
        else:
            tmp_file = tempfile.TemporaryFile("w+b")
        
            controller = self.storage.download(path, tmp_file)
            yield controller

            controller.work()

            tmp_file.seek(0)

            yield tmp_file

    def get_encrypted_file(self, path):
        path = Paths.join(self.prefix, path)

        if self.encrypted:
            path = self.encrypt_path(path)

            tmp_file = tempfile.TemporaryFile("w+b")

            controller = self.storage.download(path, tmp_file)
            yield controller

            controller.work()

            tmp_file.seek(0)

            yield tmp_file
        else:
            with tempfile.TemporaryFile("w+b") as tmp_file:
                controller = self.storage.download(path, tmp_file)
                yield controller

                controller.work()

                tmp_file.seek(0)

                result = self.config.temp_encrypt(tmp_file)

            yield result
