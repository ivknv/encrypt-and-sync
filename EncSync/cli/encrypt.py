#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import os

from .common import show_error, ask_master_password
from . import common
from ..EncSync import EncSync, InvalidConfigError

READ_BLOCK_SIZE = 1024 ** 2 # Bytes

def encrypt(env, paths):
    assert(len(paths) > 0)

    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    if len(paths) == 1:
        dest = paths[0]
    else:
        dest = paths.pop()
        if len(paths) > 2 and not os.path.isdir(dest):
            show_error("Error: destination must be a directory")
            return 1

    for path in paths:
        try:
            f = encsync.temp_encrypt(path)
        except FileNotFoundError:
            show_error("Error: no such file or directory: %r" % path)
            return 1
        except IsADirectoryError:
            show_error("Error: %r is a directory" % path)
            return 1

        if os.path.isdir(dest):
            out_path = os.path.join(dest, os.path.split(path)[1])
        else:
            out_path = dest

        try:
            with open(out_path, "wb") as out:
                block = f.read(READ_BLOCK_SIZE)
                while block:
                    out.write(block)
                    block = f.read(READ_BLOCK_SIZE)
        except FileNotFoundError:
            show_error("Error: no such file or directory: %r" % out_path)
            return 1
        except IsADirectoryError:
            show_error("Error: %r is a directory" % out_path)
            return 1

    return 0

def encrypt_config(env, in_path, out_path=None):
    if out_path is None:
        out_path = in_path

    if os.path.isdir(out_path):
        show_error("Error: %r is a directory" % out_path)
        return 1

    try:
        config = EncSync.load_config(in_path, None, False)

        valid, msg = EncSync.validate_config(config)

        if not valid:
            raise InvalidConfigError(msg)
    except InvalidConfigError as e:
        show_error("Error: invalid configuration: %s" % e)
        return 1
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % in_path)
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % in_path)
        return 1

    while True:
        master_password = ask_master_password("Master password to encrypt with: ")

        if master_password is None:
            return 130

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
        return 1
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % out_path)
        return 1

    return 0

def encrypt_filename(env, paths, prefix):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    for path in paths:
        print(encsync.encrypt_path(path, prefix)[0])

    return 0
