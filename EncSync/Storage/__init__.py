# -*- coding: utf-8 -*-

from .Storage import Storage
from .LocalStorage import LocalStorage
from .YaDiskStorage import YaDiskStorage
from .DropboxStorage import DropboxStorage

__all__ = ["Storage", "LocalStorage", "YaDiskStorage", "DropboxStorage"]

LocalStorage.register()
YaDiskStorage.register()
DropboxStorage.register()
