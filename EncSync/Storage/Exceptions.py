# -*- coding: utf-8 -*-

__all__ = ["StorageException", "StorageError", "ControllerInterrupt",
           "TemporaryStorageError", "UnknownStorageError"]

class StorageException(Exception):
    pass

class StorageError(StorageException):
    pass

class ControllerInterrupt(StorageException):
    pass

class TemporaryStorageError(StorageError):
    pass

class UnknownStorageError(StorageError):
    def __init__(self, name, msg=None):
        if msg is None:
            msg = "Unknown storage: %r" % (name,)

        StorageError.__init__(self, msg)

        self.name = name
