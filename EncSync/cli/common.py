#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from getpass import getpass
import hashlib
import json
import sys
import os

from ..EncSync import EncSync, InvalidConfigError
from ..Encryption import DecryptionError
from .. import Paths

try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError

def positive_int(arg):
    try:
        n = int(arg)
        if n > 0:
            return n
    except ValueError:
        pass

    raise argparse.ArgumentTypeError("%r is not a positive integer" % arg)

def local_path(arg):
    path_type = recognize_path(arg)[1]

    if path_type == "local":
        return arg

    raise argparse.ArgumentTypeError("%r is not a local path" % arg)

def remote_path(arg):
    path_type = recognize_path(arg)[1]

    if path_type == "remote":
        return arg

    raise argparse.ArgumentTypeError("%r is not a local path" % arg)

def non_local_path(arg):
    path_type = recognize_path(arg, "remote")[1]

    if path_type != "local":
        return arg

    raise argparse.ArgumentTypeError("%r is a local path" % arg)

def non_remote_path(arg):
    path_type = recognize_path(arg, "local")[1]

    if path_type != "remote":
        return arg

    raise argparse.ArgumentTypeError("%r is a remote path" % arg)

def recognize_path(path, default="local"):
    if path.startswith("disk://"):
        path = path[7:]
        path_type = "remote"
    elif path.startswith("local://"):
        path_type = "local"
        path = path[8:]
    else:
        path_type = default

    return (path, path_type)

def prepare_remote_path(path, cwd="/"):
    return Paths.join(cwd, path)

def authenticate(env, config_path, master_password=None):
    if not os.path.exists(config_path):
        show_error("Error: file not found: %r" % config_path)
        return None, 1
    elif os.path.isdir(config_path):
        show_error("Error: %r is a directory" % config_path)
        return None, 1

    if master_password is None:
        master_password = env.get("master_password", None)

    if master_password is None:
        master_password = ask_master_password()
        if master_password is None:
            return None, 130

    while True:
        key = hashlib.sha256(master_password.encode("utf8")).digest()

        try:
            if EncSync.check_master_key(key, config_path):
                env["master_password_sha256"] = key
                return master_password, 0
            else:
                show_error("Wrong master password. Try again")
        except FileNotFoundError:
            show_error("Error: file not found: %r" % config_path)
            return None, 1
        except IsADirectoryError:
            show_error("Error: %r is a directory" % config_path)
            return None, 1
        except DecryptionError as e:
            show_error("Error: failed to decrypt file %r: %s" % (config_path, e))
            return None, 1

        master_password = ask_master_password()

        if master_password is None:
            return None, 130

def ask_master_password(msg="Master password: "):
    try:
        return getpass(msg)
    except (KeyboardInterrupt, EOFError):
        return

def make_encsync(env, config_path=None, master_password=None):
    encsync = env.get("encsync", None)
    if encsync is not None:
        return encsync, 0

    if config_path is None:
        config_path = env["config_path"]

    master_password, ret = authenticate(env, config_path, master_password)

    if master_password is None:
        return None, ret

    encsync = EncSync(master_password)
    try:
        config = EncSync.load_config(config_path, encsync.master_key)
        encsync.set_config(config)
    except InvalidConfigError as e:
        show_error("Error: invalid configuration: %s" % e)
        return None, 1

    env["encsync"] = encsync

    return encsync, 0

def show_error(msg):
    print(msg, file=sys.stderr)

def display_table(y, x, stdscr, header, rows, colors=tuple()):
    paddings = [1] * len(header)
    paddings[0] = 0

    max_width = 0

    for row in [header] + rows:
        row_width = 0
        for col, i in zip(row, range(len(row))):
            width = len(col) + 1
            row_width += width
            if i + 1 < len(row):
                paddings[i + 1] = max(paddings[i + 1], width)
            else:
                row_width -= 1
        max_width = max(max_width, row_width)

    for row, i in zip([header] + rows, range(len(rows) + 1)):
        offset = 0

        if len(colors):
            color_pair = colors[i % len(colors)]
        else:
            color_pair = None

        if color_pair is not None:
            stdscr.addstr(y + i, x, " " * max_width, color_pair)

        for col, pad_len in zip(row, paddings):
            offset += pad_len

            if color_pair is not None:
                stdscr.addstr(y + i, x + offset, col, color_pair)
            else:
                stdscr.addstr(y + i, x + offset, col)

    height = len(rows) + 1

    return height
