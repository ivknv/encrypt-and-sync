#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from getpass import getpass
import hashlib
import json
import sys

from ..EncSync import EncSync

try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError

global_vars = {}

def positive_int(arg):
    try:
        n = int(arg)
        if n > 0:
            return n
    except ValueError:
        pass

    raise argparse.ArgumentTypeError("%r is not a positive integer" % arg)

def local_path(arg):
    path, path_type = recognize_path(arg)

    if path_type == "local":
        return arg

    raise argparse.ArgumentTypeError("%r is not a local path" % arg)

def remote_path(arg):
    path, path_type = recognize_path(arg)

    if path_type == "remote":
        return arg

    raise argparse.ArgumentTypeError("%r is not a local path" % arg)

def non_local_path(arg):
    path, path_type = recognize_path(arg, "remote")

    if path_type != "local":
        return arg

    raise argparse.ArgumentTypeError("%r is a local path" % arg)

def non_remote_path(arg):
    path, path_type = recognize_path(arg, "local")

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

def make_encsync(config_path=None, master_password=None):
    encsync = global_vars.get("encsync", None)
    if encsync is not None:
        return encsync

    if config_path is None:
        config_path = global_vars.get("config", None)

    if master_password is None:
        master_password = global_vars.get("master_password", None)

    while True:
        try:
            if master_password is None:
                password = getpass("Master password: ")
            else:
                password = master_password

            encsync = EncSync(password)
            encsync.load_config(config_path)

            global_vars["encsync"] = encsync
            global_vars["master_password_sha256"] = hashlib.sha256(password.encode("utf8")).digest()

            return encsync
        except (UnicodeDecodeError, JSONDecodeError):
            show_error("Wrong master password. Try again")

def show_info(msg, verbose=False):
    if (verbose and global_vars.get("verbose", False)) or not verbose:
        print(msg)

def show_error(msg):
    print(msg, file=sys.stderr)

def display_table(y, x, stdscr, header, rows, colors=[]):
    paddings = [1] * len(header)
    paddings[0] = 0

    max_width = 0

    for row in ([header] + rows):
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
