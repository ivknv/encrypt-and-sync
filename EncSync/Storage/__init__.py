# -*- coding: utf-8 -*-

from .Storage import Storage
from .LocalStorage import LocalStorage
from .YaDiskStorage import YaDiskStorage
from .Exceptions import UnknownStorageError

__all__ = ["Storage", "LocalStorage", "YaDiskStorage", "get_storage"]

STORAGE_TABLE = {s.name: s for s in [LocalStorage, YaDiskStorage]}

def get_storage(name):
    """
        Get storage class by name.

        :param name: `str`, storage name

        :returns: corresponding `Storage`-based class
    """

    try:
        return STORAGE_TABLE[name]
    except KeyError:
        raise UnknownStorageError(name)
