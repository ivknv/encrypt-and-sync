#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["SynchronizerError", "LocalPathNotFoundError", "TooLongFilenameError"]

class SynchronizerError(BaseException):
    pass

class LocalPathNotFoundError(SynchronizerError):
    def __init__(self, msg, path):
        SynchronizerError.__init__(self, msg)
        self.path = path

class TooLongFilenameError(SynchronizerError):
    def __init__(self, msg, filename):
        SynchronizerError.__init__(self, msg)
        self.filename = filename
