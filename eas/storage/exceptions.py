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

class UnknownStorageError(KeyError):
    pass
