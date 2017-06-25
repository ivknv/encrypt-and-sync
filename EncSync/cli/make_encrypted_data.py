#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import os
from .common import ask_master_password, show_error
from ..EncSync import EncSync

def make_encrypted_data(env, path):
    if os.path.isdir(path):
        show_error("Error: %r is a directory" % path)
        return 1

    while True:
        key = ask_master_password("Enter a new key: ")

        if key is None:
            return 130

        confirm = ask_master_password("Confirm key: ")

        if confirm == key:
            break

    enc_data = {"key":            key,
                "yandexAppToken": ""}

    while True:
        master_password = ask_master_password("New master password: ")

        if master_password is None:
            return 130

        confirm = ask_master_password("Confirm master password: ")

        if confirm == master_password:
            break

    key = hashlib.sha256(master_password.encode("utf8")).digest()

    try:
        EncSync.store_encrypted_data(enc_data, path, key)
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % path)
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % path)
        return 1

    return 0
