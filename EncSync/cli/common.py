#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from getpass import getpass
import json
import sys
import os

from ..Config import Config
from ..Config.utils import check_master_key
from ..Config.Exceptions import InvalidConfigError, InvalidEncryptedDataError
from ..Downloader import DownloadTask
from ..Synchronizer import SyncTask
from ..DuplicateRemover import DuplicateRemoverTask
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
    if target.expected_total_children == -1:
        return 0.0

    n = target.progress["finished"] + target.progress["skipped"]

    try:
        return float(n) / target.total_children * 100.0
    except ZeroDivisionError:
        return 100.0

def get_failed_percent(target):
    if target.expected_total_children == -1:
        return 0.0

    try:
        return float(target.progress["failed"]) / target.total_children * 100.0
    except ZeroDivisionError:
        return 0.0

def get_progress_str(task):
    assert(isinstance(task, (SyncTask, DownloadTask, DuplicateRemoverTask)))

    target = task.parent
    finished_percent = get_finished_percent(target)
    failed_percent = get_failed_percent(target)

    if isinstance(task, SyncTask):
        path = task.path
    elif isinstance(task, DownloadTask):
        path = task.src_path
    else:
        path = task.path

    if target.expected_total_children == -1:
        return "[N/A][%s]" % (path,)

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

    raise argparse.ArgumentTypeError("%r is not a remote path" % arg)

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
    before, div, after = path.partition("://")

    if not div:
        return (before, default)

    sub_map = {"disk": "yadisk"}

    before = sub_map.get(before, before)

    return (after, before)

def prepare_remote_path(path, cwd="/"):
    return Paths.join(cwd, path)

def authenticate(env, enc_data_path, master_password=None):
    if not os.path.exists(enc_data_path):
        show_error("Error: file not found: %r" % (enc_data_path,))
        return None, 1
    elif os.path.isdir(enc_data_path):
        show_error("Error: %r is a directory" % (enc_data_path,))
        return None, 1

    if master_password is None:
        master_password = env.get("master_password", None)

    if master_password is None:
        master_password = ask_master_password()
        if master_password is None:
            return None, 130

    while True:
        key = Config.encode_key(master_password)

        try:
            if check_master_key(key, enc_data_path):
                env["master_password_sha256"] = key
                return master_password, 0
            else:
                show_error("Wrong master password. Try again")
        except FileNotFoundError:
            show_error("Error: file not found: %r" % (enc_data_path,))
            return None, 1
        except IsADirectoryError:
            show_error("Error: %r is a directory" % (enc_data_path,))
            return None, 1
        except DecryptionError as e:
            show_error("Error: failed to decrypt file %r: %s" % (enc_data_path, e))
            return None, 1

        master_password = ask_master_password()

        if master_password is None:
            return None, 130

def ask_master_password(msg="Master password: "):
    try:
        return getpass(msg)
    except (KeyboardInterrupt, EOFError):
        return

def make_config(env, enc_data_path=None, config_path=None, master_password=None):
    config = env.get("config", None)
    if config is not None:
        return config, 0

    if config_path is None:
        config_path = env["config_path"]

    if enc_data_path is None:
        enc_data_path = env["enc_data_path"]

    master_password, ret = authenticate(env, enc_data_path, master_password)

    if master_password is None:
        return None, ret

    try:
        config = Config.load(config_path)
        config.master_password = master_password
    except InvalidConfigError as e:
        show_error("Error: invalid configuration: %s" % (e,))
        return None, 1

    try:
        config.load_encrypted_data(enc_data_path)
    except InvalidEncryptedDataError:
        show_error("Error: invalid encrypted data")
        return None, 1

    env["config"] = config

    return config, 0

def show_error(msg):
    print(msg, file=sys.stderr)

def create_encsync_dirs(env):
    paths = (env["config_dir"], env["db_dir"])

    for path in paths:
        try:
            os.mkdir(path, mode=0o755)
        except FileExistsError:
            pass
        except FileNotFoundError:
            show_error("Error: no such file or directory: %r" % (path,))
            return 1

    return 0

def cleanup_filelists(env):
    config = env["config"]
    files = os.listdir(env["db_dir"])

    target_names = set(config.targets.keys())

    suffixes = ("-local-filelist.db", "-yadisk-filelist.db",
                "-local-duplicates.db", "-yadisk-duplicates.db")

    for filename in files:
        suffix = None

        for s in suffixes:
            if filename.endswith(s):
                suffix = s
                break

        if suffix is None:
            continue

        name = filename.rsplit(suffix, 1)[0]

        if name not in target_names:
            try:
                os.remove(os.path.join(env["db_dir"], filename))
            except (FileNotFoundError, IsADirectoryError, PermissionError):
                pass
