# -*- coding: utf-8 -*-

import importlib

from .Storage import Storage

__all__ = ["Storage"]

Storage.register_lazy("local", lambda: importlib.import_module("EncSync.Storage.LocalStorage").LocalStorage)
Storage.register_lazy("yadisk", lambda: importlib.import_module("EncSync.Storage.YaDiskStorage").YaDiskStorage)
Storage.register_lazy("dropbox", lambda: importlib.import_module("EncSync.Storage.DropboxStorage").DropboxStorage)
Storage.register_lazy("sftp", lambda: importlib.import_module("EncSync.Storage.SFTPStorage").SFTPStorage)
