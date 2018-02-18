#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from copy import deepcopy
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

__all__ = ["positive_int", "get_finished_percent", "get_failed_percent",
           "get_progress_str", "make_size_readable", "local_path", "remote_path",
           "non_local_path", "non_remote_path", "recognize_path", "prepare_remote_path",
           "authenticate", "ask_master_password", "make_config", "show_error",
           "create_encsync_dirs", "cleanup_filelists"]

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

def make_size_readable(size, suffixes=None):
    if suffixes is None:
        suffixes= [" B", " KiB", " MiB", " GiB", " TiB"]

    suffix = suffixes[0]

    for s in suffixes[1:]:
        if size >= 1024:
            suffix = s
            size = float(size) / 1024

    d = round(size - int(size), 2)

    if d < 0.01:
        return "%d%s" % (size, suffix)
    elif int(d * 100) % 10 == 0:
        return "%.1f%s" % (size, suffix)

    return "%.2f%s" % (size, suffix)

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

def authenticate(env, enc_data_path):
    if not os.path.exists(enc_data_path):
        show_error("Error: file not found: %r" % (enc_data_path,))
        return None, 1
    elif os.path.isdir(enc_data_path):
        show_error("Error: %r is a directory" % (enc_data_path,))
        return None, 1

    master_password = env.get("master_password")

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

def make_config(env, load_encrypted_data=True, raw=False):
    raw_config = env.get("raw_config")
    config = env.get("config")

    if raw and raw_config is not None and (raw_config.encrypted_data or not load_encrypted_data):
        return raw_config, 0

    if config is not None and (config.encrypted_data or not load_encrypted_data):
        return config, 0

    config_path = env["config_path"]
    enc_data_path = env["enc_data_path"]

    if raw_config is None:
        try:
            raw_config = Config.load(config_path)

        except InvalidConfigError as e:
            show_error("Error: invalid configuration: %s" % (e,))
            return None, 1

    if load_encrypted_data:
        master_password, ret = authenticate(env, enc_data_path)

        if master_password is None:
            return None, ret

        raw_config.master_password = master_password

        try:
            raw_config.load_encrypted_data(enc_data_path)
        except InvalidEncryptedDataError:
            show_error("Error: invalid encrypted data")
            return None, 1

    env["raw_config"] = raw_config

    if not raw:
        config = deepcopy(raw_config)
        config.process()

    env["config"] = config

    if raw:
        return raw_config, 0

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

    folder_names = {i for i in config.folders.keys()}
    storage_names = {i["type"] for i in config.folders.values()}

    filelist_suffix = "-filelist.db"
    duplicates_suffix = "-duplicates.db"

    suffixes = (filelist_suffix, duplicates_suffix)

    for filename in files:
        suffix = None

        for s in suffixes:
            if filename.endswith(s):
                suffix = s
                break

        if suffix is None:
            continue

        if suffix == filelist_suffix:
            name = filename.partition(suffix)[0]

            if name in folder_names:
                continue
        else:
            storage_name = filename.partition(suffix)[0]

            if storage_name in storage_names:
                continue

        try:
            os.remove(os.path.join(env["db_dir"], filename))
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            pass
