#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from .common import ask_master_password, show_error
from ..config import Config

__all__ = ["generate_encrypted_data"]

def generate_encrypted_data(env, path):
    if os.path.isdir(path):
        show_error("Error: %r is a directory" % path)
        return 1

    config = Config()

    while True:
        plain_key = ask_master_password("Enter a new key: ")

        if plain_key is None:
            return 130

        confirm = ask_master_password("Confirm key: ")

        if confirm == plain_key:
            break

    while True:
        master_password = ask_master_password("New master password: ")

        if master_password is None:
            return 130

        confirm = ask_master_password("Confirm master password: ")

        if confirm == master_password:
            break

    config.master_password = master_password
    config.plain_key = plain_key

    try:
        config.store_encrypted_data(path)
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % (path,))
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % (path,))
        return 1

    return 0
