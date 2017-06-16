#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from getpass import getpass
import hashlib
import json
import sys
import os

from ..EncSync import EncSync, InvalidConfigError
from ..Downloader import DownloadTask
from ..Synchronizer import SyncTask
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

def get_finished_percent(target):
    try:
        return float(target.progress["finished"]) / target.total_children * 100.0
    except ZeroDivisionError:
        return 100.0

def get_failed_percent(target):
    try:
        return float(target.progress["failed"]) / target.total_children * 100.0
    except ZeroDivisionError:
        return 0.0

def get_progress_str(task):
    assert(isinstance(task, (SyncTask, DownloadTask)))

    if isinstance(task, SyncTask):
        path = task.path.path
    elif isinstance(task, DownloadTask):
        path = task.dec_remote

    target = task.parent
    finished_percent = get_finished_percent(target)
    failed_percent = get_failed_percent(target)

    return "[%6.2f%%:%6.2f%%][%s]" % (finished_percent, failed_percent, path)

def make_size_readable(size):
    unit_list = ["KiB", "MiB", "GiB", "TiB"]
    units = "B"

    for u in unit_list:
        if size >= 1024:
            units = u
            size = float(size) / 1024

    d = round(size - int(size), 2)

    if d < 0.01:
        return "%d %s" % (size, units)
    elif int(d * 100) % 10 == 0:
        return "%.1f %s" % (size, units)

    return "%.2f %s" % (size, units)

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
