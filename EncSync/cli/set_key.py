#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..EncSync import EncSync, InvalidEncryptedDataError
from .common import ask_master_password, authenticate, show_error

def set_key(env):
    master_password, ret = authenticate(env, env["enc_data_path"])

    if master_password is None:
        return ret

    master_key = env["master_password_sha256"]

    while True:
        key = ask_master_password("New key: ")

        if key is None:
            return 130

        confirm = ask_master_password("Confirm: ")

        if confirm == key:
            break

    try:
        enc_data = EncSync.load_encrypted_data(env["enc_data_path"], master_key)
        enc_data["key"] = key

        EncSync.store_encrypted_data(enc_data, env["enc_data_path"], master_key)
    except InvalidEncryptedDataError:
        show_error("Error: invalid encrypted data")
        return 1
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % env["enc_data_path"])
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % env["enc_data_path"])
        return 1

    return 0
