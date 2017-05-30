#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import os

from .common import show_error
from . import common
from ..EncSync import EncSync, InvalidConfigError, WrongMasterKeyError

READ_BLOCK_SIZE = 1024 ** 2 # Bytes

def decrypt(env, paths):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    assert(len(paths) > 0)

    if len(paths) == 1:
        dest = paths[0]
    else:
        dest = paths.pop()
        if len(paths) > 2 and not os.path.isdir(dest):
            show_error("Error: destination must be a directory")
            return 1

    for path in paths:
        f = encsync.temp_decrypt(path)

        if os.path.isdir(dest):
            out_path = os.path.join(dest, os.path.split(path)[1])
        else:
            out_path = dest

        with open(out_path, "wb") as out:
            block = f.read(READ_BLOCK_SIZE)
            while block:
                out.write(block)
                block = f.read(READ_BLOCK_SIZE)

    return 0

def decrypt_config(env, in_path, out_path=None):
    if out_path is None:
        out_path = in_path

    if os.path.isdir(out_path):
        show_error("Error: %r is a directory" % out_path)
        return 1

    master_password, ret = common.authenticate(env, in_path)

    if master_password is None:
        return ret

    key = hashlib.sha256(master_password.encode("utf8")).digest()

    try:
        config = EncSync.load_config(in_path, key)
    except InvalidConfigError as e:
        show_error("Error: invalid configuration: %s" % e)
        return 1
    except WrongMasterKeyError:
        show_error("Error: wrong master password")
        return 1
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % in_path)
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % in_path)
        return 1

    valid, msg = EncSync.validate_config(config)

    if not valid:
        show_error("Warning: invalid configuration: %s" % msg)

    try:
        EncSync.store_config(config, out_path, None, False)
    except IsADirectoryError:
        show_error("Error: %r is a directory" % out_path)
        return 1
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % out_path)
        return 1

    return 0

def decrypt_filename(env, paths, prefix):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    for path in paths:
        print(encsync.decrypt_path(path, prefix)[0])

    return 0
