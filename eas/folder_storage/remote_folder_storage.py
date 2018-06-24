# -*- coding: utf-8 -*-

import tempfile

from .. import pathm
from .folder_storage import FolderStorage

__all__ = ["RemoteFolderStorage"]

class RemoteFolderStorage(FolderStorage):
    def get_file(self, path, *args, ivs=None, **kwargs):
        path = pathm.join(self.prefix, path)

        if self.encrypted:
            path = self.encrypt_path(path, ivs)[0]

            tmp_file = tempfile.TemporaryFile("w+b", dir=self.config.temp_dir)

            download_task = self.storage.download(path, tmp_file, *args, **kwargs)
            yield download_task

            download_task.run()

            tmp_file.seek(0)

            self.config.decrypt_file_inplace(tmp_file)
            tmp_file.seek(0)

            yield tmp_file
        else:
            tmp_file = tempfile.TemporaryFile("w+b", dir=self.config.temp_dir)
        
            download_task = self.storage.download(path, tmp_file, *args, **kwargs)
            yield download_task

            download_task.run()

            tmp_file.seek(0)

            yield tmp_file

    def get_encrypted_file(self, path, *args, ivs=None, **kwargs):
        path = pathm.join(self.prefix, path)

        if self.encrypted:
            path = self.encrypt_path(path, ivs)[0]

            tmp_file = tempfile.TemporaryFile("w+b", dir=self.config.temp_dir)

            download_task = self.storage.download(path, tmp_file, *args, **kwargs)
            yield download_task

            download_task.run()

            tmp_file.seek(0)

            yield tmp_file
        else:
            tmp_file = tempfile.TemporaryFile("w+b", dir=self.config.temp_dir)

            download_task = self.storage.download(path, tmp_file, *args, **kwargs)
            yield download_task

            download_task.run()

            tmp_file.seek(0)

            self.config.encrypt_file_inplace(tmp_file)
            tmp_file.seek(0)

            yield tmp_file
