#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["EncryptionError", "DecryptionError", "UnknownFilenameEncodingError"]

class EncryptionError(BaseException):
    pass

class DecryptionError(BaseException):
    pass

class UnknownFilenameEncodingError(BaseException):
    pass
