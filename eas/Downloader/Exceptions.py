#!/usr/bin/env python
# -*- coding: utf-8 -*-

class DownloaderError(Exception):
    pass

class NotFoundInDBError(DownloaderError):
    def __init__(self, msg, path):
        self.path = path
        DownloaderError.__init__(self, msg)

class FailedToObtainLinkError(DownloaderError):
    def __init__(self, msg, path):
        self.path = path
        DownloaderError.__init__(self, msg)
