#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from ..constants import CONFIG_TEST
from .. import encryption

from .exceptions import InvalidEncryptedDataError, WrongMasterKeyError

__all__ = ["load_encrypted_data", "store_encrypted_data", "check_master_key"]

try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError

def load_encrypted_data(path_or_file, master_key, enable_test=True):
    if isinstance(path_or_file, (str, bytes)):
        file = open(path_or_file, "rb")
        close_file = True
    else:
        file = path_or_file
        close_file = False

    try:
        data = file.read()

        if master_key is not None:
            data = encryption.decrypt_data(data, master_key)

        test_string = data[:len(CONFIG_TEST)]

        if test_string != CONFIG_TEST:
            if master_key is not None:
                raise WrongMasterKeyError("wrong master key")
            elif enable_test:
                raise InvalidEncryptedDataError("test string is missing")
        else:
            data = data[len(CONFIG_TEST):]

        try:
            data = data.decode("utf8")
        except UnicodeDecodeError:
            raise InvalidEncryptedDataError("failed to decode")

        try:
            enc_data = json.loads(data)
        except JSONDecodeError:
            raise InvalidEncryptedDataError("not proper JSON")

        return enc_data
    finally:
        if close_file:
            file.close()

def store_encrypted_data(enc_data, path_or_file, master_key, enable_test=True):
    js = json.dumps(enc_data).encode("utf8")

    if enable_test:
        js = CONFIG_TEST + js

    if master_key is not None:
        js = encryption.encrypt_data(js, master_key)

    if isinstance(path_or_file, (str, bytes)):
        file = open(path_or_file, "wb")
        close_file = True
    else:
        file = path_or_file
        close_file = False

    try:
        file.write(js)
    finally:
        if close_file:
            file.close()

def check_master_key(master_key, path_or_file):
    if isinstance(path_or_file, (str, bytes)):
        file = open(path_or_file, "rb")
        close_file = True
    else:
        file = path_or_file
        close_file = False

    try:
        data = encryption.decrypt_data(file.read(), master_key)
        return data[:len(CONFIG_TEST)] == CONFIG_TEST
    finally:
        if close_file:
            file.close()
