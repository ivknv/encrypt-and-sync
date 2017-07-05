#!/usr/bin/env python
# -*- coding: utf-8 -*-

class SynchronizerError(BaseException):
    pass

class TooLongFilenameError(SynchronizerError):
    def __init__(self, msg, filename):
        SynchronizerError.__init__(self, msg)
        self.filename = filename
