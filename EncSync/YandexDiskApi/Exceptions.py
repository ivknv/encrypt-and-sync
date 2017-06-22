#!/usr/bin/env python
# -*- coding: utf-8 -*-

class YandexDiskError(BaseException):
    def __init__(self, error_type=None, msg=""):
        BaseException.__init__(self, msg)

        self.error_type = error_type

class UnknownYandexDiskError(YandexDiskError):
    def __init__(self, msg=""):
        YandexDiskError.__init__(self, None, msg)

class DiskNotFoundError(YandexDiskError):
    error_type = "DiskNotFoundError"

    def __init__(self, msg=""):
        YandexDiskError.__init__(self, DiskNotFoundError.error_type, msg)

class PathNotFoundError(YandexDiskError):
    error_type = "DiskPathDoesntExistsError"

    def __init__(self, msg=""):
        YandexDiskError.__init__(self, PathNotFoundError.error_type, msg)

class DirectoryExistsError(YandexDiskError):
    error_type = "DiskPathPointsToExistentDirectoryError"

    def __init__(self, msg=""):
        YandexDiskError.__init__(self, DirectoryExistsError.error_type, msg)

class PathExistsError(YandexDiskError):
    error_type = "DiskResourceAlreadyExistsError"

    def __init__(self, msg=""):
        YandexDiskError.__init__(self, PathExistsError.error_type, msg)

exception_map = {DiskNotFoundError.error_type: DiskNotFoundError,
                 PathNotFoundError.error_type: PathNotFoundError,
                 DirectoryExistsError.error_type: DirectoryExistsError,
                 PathExistsError.error_type: PathExistsError}
