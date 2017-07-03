#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys

from .cli import common
from .cli.Environment import Environment
from .cli.scan import do_scan
from .cli.show_diffs import show_diffs
from .cli.sync import do_sync
from .cli.download import download
from .cli.check_token import check_token
from .cli.encrypt import encrypt, encrypt_filename
from .cli.decrypt import decrypt, decrypt_filename
from .cli.show_duplicates import show_duplicates
from .cli.make_config import make_config
from .cli.make_encrypted_data import make_encrypted_data
from .cli.Console import run_console
from .cli.execute import execute, execute_script
from .cli.set_key import set_key
from .cli.get_key import get_key
from .cli.set_master_password import set_master_password
from .cli.password_prompt import password_prompt

def cleanup(env):
    try:
        os.remove(os.path.join(env["config_dir"], "encsync_diffs.db"))
    except (FileNotFoundError, IsADirectoryError):
        pass

def any_not_none(keys, container):
    for key in keys:
        if getattr(container, key) is not None:
            return True

    return False

def setup_logging(env):
    import logging
    from . import Downloader, Synchronizer, Scanner, CentDB

    loggers = ((Downloader.Logging.logger, "downloader.log"),
               (Synchronizer.Logging.logger, "synchronizer.log"),
               (Scanner.Logging.logger, "scanner.log"),
               (CentDB.Logging.logger, "centdb.log"))

    for logger, filename in loggers:
        formatter = logging.Formatter("%(asctime)s - %(name)s-Thread-%(thread)d: %(message)s")

        path = os.path.join(env["config_dir"], filename)

        handler = logging.FileHandler(path)
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)

        logger.addHandler(handler)

def main(args=None):
    if args is None:
        args = sys.argv

    ns = parse_args(args)

    env = Environment()
    
    if ns.master_password is None and not ns.force_ask_password and not ns.password_prompt:
        try:
            env["master_password"] = os.environ["ENCSYNC_MASTER_PASSWORD"]
        except KeyError:
            pass
    else:
        env["master_password"] = ns.master_password

    env["ask"] = ns.ask
    env["no_choice"] = ns.no_choice
    env["no_check"] = not ns.integrity_check
    env["no_scan"] = ns.no_scan
    env["no_diffs"] = ns.no_diffs
    env["all"] = ns.all
    env["local_only"] = ns.local_only
    env["remote_only"] = ns.remote_only

    if ns.n_workers is not None:
        env["n_workers"] = ns.n_workers

    if ns.config_dir is not None or env.get("config_dir", None) is None:
        if ns.config_dir is None:
            ns.config_dir = "~/.encsync"

        env["config_dir"] = os.path.realpath(os.path.expanduser(ns.config_dir))
        env["config_path"] = os.path.join(env["config_dir"], "encsync.conf")
        env["enc_data_path"] = os.path.join(env["config_dir"], "encrypted_data.json")

    common.create_config_dir(env)
    if not os.path.exists(env["config_path"]):
        make_config(env, env["config_path"])

    if not os.path.exists(env["enc_data_path"]):
        make_encrypted_data(env, env["enc_data_path"])

    setup_logging(env)

    cleanup(env)

    actions = (("scan", lambda: do_scan(env, ns.scan)),
               ("sync", lambda: do_sync(env, ns.sync)),
               ("show_diffs", lambda: show_diffs(env, *ns.show_diffs[:2])),
               ("download", lambda: download(env, ns.download)),
               ("encrypt", lambda: encrypt(env, ns.encrypt)),
               ("encrypt_filename", lambda: encrypt_filename(env,
                                                             ns.encrypt_filename,
                                                             ns.prefix or "/")),
               ("decrypt", lambda: decrypt(env, ns.decrypt)),
               ("decrypt_filename", lambda: decrypt_filename(env,
                                                             ns.decrypt_filename,
                                                             ns.prefix or "/")),
               ("show_duplicates", lambda: show_duplicates(env, ns.show_duplicates)),
               ("console", lambda: run_console(env)),
               ("make_config", lambda: make_config(env, ns.make_config)),
               ("execute", lambda: execute(env, ns.execute)),
               ("execute_script", lambda: execute_script(env, ns.execute_script)),
               ("set_key", lambda: set_key(env)),
               ("get_key", lambda: get_key(env)),
               ("set_master_password", lambda: set_master_password(env)),
               ("password_prompt", lambda: password_prompt(env)))

    if any_not_none(("scan", "sync", "download", "show_diffs", "console"), ns):
        if not ns.no_token_check:
            ret = check_token(env)
            if ret:
                return ret

    for key, func in actions:
        if getattr(ns, key) is not None:
            return func()

def positive_int(arg):
    try:
        n = int(arg)
        if n > 0:
            return n
    except ValueError:
        pass

    raise argparse.ArgumentTypeError("%r is not a positive integer" % arg)

def parse_args(args):
    parser = argparse.ArgumentParser(description="Synchronizes encrypted files",
                                     prog=args[0])

    parser.add_argument("--master-password", default=None)
    parser.add_argument("--force-ask-password", action="store_true")
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--no-scan", action="store_true")
    parser.add_argument("--no-choice", action="store_true")
    parser.add_argument("--no-diffs", action="store_true")
    parser.add_argument("--no-token-check", action="store_true")
    parser.add_argument("--ask", action="store_true")
    parser.add_argument("-a", "--all", action="store_true")
    parser.add_argument("-I", "--integrity-check", action="store_true")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--local-only", action="store_true")
    group.add_argument("--remote-only", action="store_true")

    config_group = parser.add_argument_group("config")
    config_group.add_argument("-c", "--config-dir", metavar="PATH", default=None)
    config_group.add_argument("--n-workers", "-w", type=positive_int)

    actions_group = parser.add_mutually_exclusive_group()
    actions_group.add_argument("-s", "--scan", nargs="*")
    actions_group.add_argument("-d", "--show-diffs", nargs=2)
    actions_group.add_argument("-S", "--sync", nargs="*")
    actions_group.add_argument("-D", "--download", nargs="+")
    actions_group.add_argument("--encrypt", nargs="+")
    actions_group.add_argument("--decrypt", nargs="+")
    actions_group.add_argument("--encrypt-filename", nargs="+")
    actions_group.add_argument("--decrypt-filename", nargs="+")
    actions_group.add_argument("--show-duplicates", nargs="+")
    actions_group.add_argument("--console", default=None, action="store_true")
    actions_group.add_argument("--make-config")
    actions_group.add_argument("-e", "--execute")
    actions_group.add_argument("-E", "--execute-script")
    actions_group.add_argument("--set-key", default=None, action="store_true")
    actions_group.add_argument("--get-key", default=None, action="store_true")
    actions_group.add_argument("--set-master-password", default=None, action="store_true")
    actions_group.add_argument("--password-prompt", default=None, action="store_true")

    return parser.parse_args(args[1:])

if __name__ == "__main__":
    sys.exit(main(sys.argv))
