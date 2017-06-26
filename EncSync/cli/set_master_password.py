#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib

from ..EncSync import EncSync, InvalidEncryptedDataError
from .common import ask_master_password, authenticate, show_error

def set_master_password(env):
    cur_master_password, ret = authenticate(env, env["enc_data_path"])

    if cur_master_password is None:
        return ret

    cur_master_key = env["master_password_sha256"]

    try:
        enc_data = EncSync.load_encrypted_data(env["enc_data_path"], cur_master_key)
    except InvalidEncryptedDataError:
        show_error("Error: invalid encrypted data")
        return 1
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % env["enc_data_path"])
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % env["enc_data_path"])
        return 1

    while True:
        new_master_password = ask_master_password("New master password: ")

        if new_master_password is None:
            return 130

        confirm = ask_master_password("Confirm: ")

        if confirm == new_master_password:
            break

    new_master_key = hashlib.sha256(new_master_password.encode("utf8")).digest()

    try:
        EncSync.store_encrypted_data(enc_data, env["enc_data_path"], new_master_key)
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % env["enc_data_path"])
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % env["enc_data_path"])
        return 1

    return 0
