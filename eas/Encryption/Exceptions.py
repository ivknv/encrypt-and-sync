#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["EncryptionError", "DecryptionError", "UnknownFilenameEncodingError"]

class EncryptionError(Exception):
    pass

class DecryptionError(Exception):
    pass

class UnknownFilenameEncodingError(Exception):
    pass
