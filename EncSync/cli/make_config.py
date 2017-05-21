#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import os

from .common import ask_master_password, show_error
from ..EncSync import EncSync

def make_config(path):
    if os.path.isdir(path):
        show_error("Error: %r is a directory" % path)
        return

    e = EncSync("")
    config = e.make_config()
    del e

    while True:
        master_password = ask_master_password("Master password for %r: " % path)

        if master_password is None:
            return

        confirm = ask_master_password("Confirm master password: ")

        if confirm == master_password:
            break

    key = hashlib.sha256(master_password.encode("utf8")).digest()

    try:
        EncSync.store_config(config, path, key)
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % path)
    except IsADirectoryError:
        show_error("Error: %r is a directory" % path)
