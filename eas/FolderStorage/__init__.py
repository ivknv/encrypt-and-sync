# -*- coding: utf-8 -*-

from ..Storage import Storage

from .FolderStorage import *
from .LocalFolderStorage import *
from .RemoteFolderStorage import *

__all__ = ["FolderStorage", "LocalFolderStorage", "RemoteFolderStorage",
           "get_folder_storage"]

def get_folder_storage(name):
    TABLE = {"local": LocalFolderStorage,
             "remote": RemoteFolderStorage}

    return TABLE[Storage.get_storage(name).type]
