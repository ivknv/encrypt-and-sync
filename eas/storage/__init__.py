# -*- coding: utf-8 -*-

import importlib

from .storage import Storage

__all__ = ["Storage"]

def _get_yadisk_storage():
    try:
        return importlib.import_module("eas.storage.yadisk_storage").YaDiskStorage
    except ImportError as e:
        if e.name in ("yadisk", "requests"):
            raise ImportError("Missing optional dependency: %r" % (e.name,), name=e.name)

        raise e

def _get_dropbox_storage():
    try:
        return importlib.import_module("eas.storage.dropbox_storage").DropboxStorage
    except ImportError as e:
        if e.name in ("dropbox", "requests"):
            raise ImportError("Missing optional dependency: %r" % (e.name,), name=e.name)

        raise e

def _get_sftp_storage():
    try:
        return importlib.import_module("eas.storage.sftp_storage").SFTPStorage
    except ImportError as e:
        if e.name in ("pysftp", "paramiko"):
            raise ImportError("Missing optional dependency: %r" % (e.name,), name=e.name)

        raise e

Storage.register_lazy("local", lambda: importlib.import_module("eas.storage.local_storage").LocalStorage)
Storage.register_lazy("yadisk", _get_yadisk_storage)
Storage.register_lazy("dropbox", _get_dropbox_storage)
Storage.register_lazy("sftp", _get_sftp_storage)
