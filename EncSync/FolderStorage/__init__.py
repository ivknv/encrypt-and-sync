# -*- coding: utf-8 -*-

from ..Storage.Exceptions import UnknownStorageError

from .FolderStorage import *
from .LocalFolderStorage import *
from .RemoteFolderStorage import *

__all__ = ["FolderStorage", "LocalFolderStorage", "RemoteFolderStorage",
           "get_folder_storage"]

FOLDER_STORAGE_TABLE = {"local": LocalFolderStorage,
                        "yadisk": RemoteFolderStorage}

def get_folder_storage(name):
    try:
        return FOLDER_STORAGE_TABLE[name]
    except KeyError:
        raise UnknownStorageError(name)
