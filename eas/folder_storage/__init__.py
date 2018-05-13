# -*- coding: utf-8 -*-

from ..storage import Storage

from .folder_storage import *
from .local_folder_storage import *
from .remote_folder_storage import *

__all__ = ["FolderStorage", "LocalFolderStorage", "RemoteFolderStorage",
           "get_folder_storage"]

def get_folder_storage(name):
    TABLE = {"local": LocalFolderStorage,
             "remote": RemoteFolderStorage}

    return TABLE[Storage.get_storage(name).type]
