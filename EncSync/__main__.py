#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse

from .cli.Environment import Environment
from .cli.scan import do_scan
from .cli.show_diffs import show_diffs
from .cli.sync import do_sync
from .cli.download import download
from .cli.check_token import check_token
from .cli.encrypt import encrypt, encrypt_config, encrypt_filename
from .cli.decrypt import decrypt, decrypt_config, decrypt_filename
from .cli.show_duplicates import show_duplicates
from .cli.make_config import make_config
from .cli.Console import run_console
from .cli.execute import execute, execute_script

def any_not_none(keys, container):
    for key in keys:
        if getattr(container, key) is not None:
            return True

    return False

def main(args):
    ns = parse_args(args)

    env = Environment()

    env["master_password"] = ns.master_password
    env["config_path"] = ns.config

    actions = (("scan", lambda: do_scan(env, ns.scan, ns.n_workers)),
               ("sync", lambda: do_sync(env, ns.sync, ns.n_workers)),
               ("show_diffs", lambda: show_diffs(env, *ns.show_diffs[:2])),
               ("download", lambda: download(env, ns.download, ns.n_workers)),
               ("encrypt", lambda: encrypt(env, ns.encrypt)),
               ("encrypt_filename", lambda: encrypt_filename(env,
                                                             ns.encrypt_filename,
                                                             ns.prefix or "/")),
               ("encrypt_config", lambda: encrypt_config(env, *ns.encrypt_config[:2])),
               ("decrypt", lambda: decrypt(env, ns.decrypt)),
               ("decrypt_filename", lambda: decrypt_filename(env,
                                                             ns.decrypt_filename,
                                                             ns.prefix or "/")),
               ("decrypt_config", lambda: decrypt_config(env, *ns.decrypt_config[:2])),
               ("show_duplicates", lambda: show_duplicates(env, ns.show_duplicates)),
               ("console", lambda: run_console(env)),
               ("make_config", lambda: make_config(env, ns.make_config)),
               ("execute", lambda: execute(env, ns.execute)),
               ("execute_script", lambda: execute_script(env, ns.execute_script)))

    if any_not_none(("scan", "sync", "download", "show_diffs", "console"), ns):
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
    parser.add_argument("--prefix", default=None)

    config_group = parser.add_argument_group("config")
    config_group.add_argument("--config", metavar="PATH", default="config.json")
    config_group.add_argument("--n-workers", "-w", type=positive_int, default=1)

    actions_group = parser.add_mutually_exclusive_group()
    actions_group.add_argument("-s", "--scan", nargs="+")
    actions_group.add_argument("-d", "--show-diffs", nargs=2)
    actions_group.add_argument("-S", "--sync", nargs="+")
    actions_group.add_argument("-D", "--download", nargs="+")
    actions_group.add_argument("--encrypt", nargs="+")
    actions_group.add_argument("--decrypt", nargs="+")
    actions_group.add_argument("--encrypt-filename", nargs="+")
    actions_group.add_argument("--decrypt-filename", nargs="+")
    actions_group.add_argument("--encrypt-config", nargs="+")
    actions_group.add_argument("--decrypt-config", nargs="+")
    actions_group.add_argument("--show-duplicates", nargs="+")
    actions_group.add_argument("--console", default=None, action="store_true")
    actions_group.add_argument("--make-config")
    actions_group.add_argument("-e", "--execute")
    actions_group.add_argument("-E", "--execute-script")

    return parser.parse_args(args[1:])

if __name__ == "__main__":
    sys.exit(main(sys.argv))
