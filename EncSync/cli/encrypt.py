#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import os
import sys

from .common import show_error, ask_master_password
from . import common
from ..EncSync import EncSync, InvalidConfigError

global_vars = common.global_vars

READ_BLOCK_SIZE = 1024 ** 2 # Bytes

def encrypt(paths):
    encsync = common.make_encsync()

    if encsync is None:
        return

    assert(len(paths) > 0)

    if len(paths) == 1:
        dest = paths[0]
    else:
        dest = paths.pop()
        if len(paths) > 2 and not os.path.isdir(dest):
            print("Error: Destination must be a directory", file=sys.stderr)
            return

    for path in paths:
        f = encsync.temp_encrypt(path)

        if os.path.isdir(dest):
            out_path = os.path.join(dest, os.path.split(path)[1])
        else:
            out_path = dest

        with open(out_path, "wb") as out:
            block = f.read(READ_BLOCK_SIZE)
            while block:
                out.write(block)
                block = f.read(READ_BLOCK_SIZE)

def encrypt_config(in_path, out_path):
    try:
        config = EncSync.load_config(in_path, None, False)

        valid, msg = EncSync.validate_config(config)

        if not valid:
            raise InvalidConfigError(msg)
    except InvalidConfigError as e:
        show_error("Error: invalid configuration: %s" % e)
        return
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % in_path)
        return
    except IsADirectoryError:
        show_error("Error: %r is a directory" % in_path)
        return

    while True:
        master_password = ask_master_password("Master password to encrypt with: ")

        if master_password is None:
            return

        confirm = ask_master_password("Confirm master password: ")

        if confirm == master_password:
            break
        elif confirm is None:
            print("")

    key = hashlib.sha256(master_password.encode("utf8")).digest()

    try:
        EncSync.store_config(config, out_path, key)
    except IsADirectoryError:
        show_error("Error: %r is a directory" % out_path)
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % out_path)

def encrypt_filename(paths, prefix):
    encsync = common.make_encsync()

    if encsync is None:
        return

    for path in paths:
        print(encsync.encrypt_path(path, prefix)[0])
