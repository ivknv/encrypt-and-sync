#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import os
import sys

from .common import show_error
from . import common
from ..EncSync import EncSync, InvalidConfigError, WrongMasterKeyError

global_vars = common.global_vars

READ_BLOCK_SIZE = 1024 ** 2 # Bytes

def decrypt(paths):
    encsync = common.make_encsync()

    if encsync is None:
        return

    assert(len(paths) > 0)

    if len(paths) == 1:
        dest = paths[0]
    else:
        dest = paths.pop()
        if len(paths) > 2 and not os.path.isdir(dest):
            print("Destination must be a directory", file=sys.stderr)
            return

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

def decrypt_config(in_path, out_path):
    if os.path.isdir(out_path):
        show_error("Error: %r is a directory" % out_path)
        return

    master_password = common.authenticate(in_path)

    if master_password is None:
        return

    key = hashlib.sha256(master_password.encode("utf8")).digest()

    try:
        config = EncSync.load_config(in_path, key)
    except InvalidConfigError as e:
        show_error("Error: invalid configuration: %s" % e)
        return
    except WrongMasterKeyError:
        show_error("Error: wrong master password")
        return
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % in_path)
        return
    except IsADirectoryError:
        show_error("Error: %r is a directory" % in_path)
        return

    valid, msg = EncSync.validate_config(config)

    if not valid:
        show_error("Warning: invalid configuration: %s" % msg)

    try:
        EncSync.store_config(config, out_path, None, False)
    except IsADirectoryError:
        show_error("Error: %r is a directory" % out_path)
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % out_path)

def decrypt_filename(paths, prefix):
    encsync = common.make_encsync()

    if encsync is None:
        return

    for path in paths:
        print(encsync.decrypt_path(path, prefix)[0])
