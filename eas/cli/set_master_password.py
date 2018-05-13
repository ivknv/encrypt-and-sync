#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..config import Config
from ..config.exceptions import InvalidEncryptedDataError
from .common import ask_master_password, authenticate, show_error

__all__ = ["set_master_password"]

def set_master_password(env):
    cur_master_password, ret = authenticate(env, env["enc_data_path"])

    if cur_master_password is None:
        return ret

    config = Config()
    config.master_password = cur_master_password

    try:
        config.load_encrypted_data(env["enc_data_path"])
    except InvalidEncryptedDataError:
        show_error("Error: invalid encrypted data")
        return 1
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % (env["enc_data_path"],))
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % (env["enc_data_path"],))
        return 1

    while True:
        new_master_password = ask_master_password("New master password: ")

        if new_master_password is None:
            return 130

        confirm = ask_master_password("Confirm: ")

        if confirm == new_master_password:
            break

    config.master_password = new_master_password

    try:
        config.store_encrypted_data(env["enc_data_path"])
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % (env["enc_data_path"],))
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % (env["enc_data_path"],))
        return 1

    return 0
