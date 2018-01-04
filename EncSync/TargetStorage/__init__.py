# -*- coding: utf-8 -*-

from ..Storage.Exceptions import UnknownStorageError

from .TargetStorage import *
from .LocalTargetStorage import *
from .RemoteTargetStorage import *

__all__ = ["TargetStorage", "LocalTargetStorage", "RemoteTargetStorage",
           "get_target_storage"]

TARGET_STORAGE_TABLE = {"local": LocalTargetStorage,
                        "yadisk": RemoteTargetStorage}

def get_target_storage(name):
    try:
        return TARGET_STORAGE_TABLE[name]
    except KeyError:
        raise UnknownStorageError(name)
