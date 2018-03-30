# -*- coding: utf-8 -*-

from ..Storage import get_storage

from .FolderStorage import *
from .LocalFolderStorage import *
from .RemoteFolderStorage import *

__all__ = ["FolderStorage", "LocalFolderStorage", "RemoteFolderStorage",
           "get_folder_storage"]

def get_folder_storage(name):
    TABLE = {"local": LocalFolderStorage,
             "remote": RemoteFolderStorage}

    return TABLE[get_storage(name).type]
