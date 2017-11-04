#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["EncryptionError", "DecryptionError"]

class EncryptionError(BaseException):
    pass

class DecryptionError(BaseException):
    pass
