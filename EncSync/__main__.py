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

def main(args):
    ns = parse_args(args)

    env = Environment()

    env["verbose"] = ns.verbose
    env["master_password"] = ns.master_password
    env["config_path"] = ns.config

    if ns.scan or ns.show_diffs or ns.sync or ns.download or ns.console:
        ret = check_token(env)
        if ret:
            return ret

    if ns.scan is not None:
        return do_scan(env, ns.scan, ns.n_workers)
    elif ns.show_diffs is not None:
        return show_diffs(env, *ns.show_diffs[:2])
    elif ns.sync is not None:
        return do_sync(env, ns.sync, ns.n_workers)
    elif ns.download is not None:
        return download(env, ns.download, ns.n_workers)
    elif ns.encrypt is not None:
        return encrypt(env, ns.encrypt)
    elif ns.decrypt is not None:
        return decrypt(env, ns.decrypt)
    elif ns.encrypt_filename is not None:
        return encrypt_filename(env, ns.encrypt_filename, ns.prefix or "/")
    elif ns.decrypt_filename is not None:
        return decrypt_filename(env, ns.decrypt_filename, ns.prefix or "/")
    elif ns.encrypt_config is not None:
        in_path = ns.encrypt_config[0]
        try:
            out_path = ns.encrypt_config[1]
        except IndexError:
            out_path = in_path

        return encrypt_config(env, in_path, out_path)
    elif ns.decrypt_config is not None:
        in_path = ns.decrypt_config[0]
        try:
            out_path = ns.decrypt_config[1]
        except IndexError:
            out_path = in_path

        return decrypt_config(env, in_path, out_path)
    elif ns.show_duplicates is not None:
        return show_duplicates(env, ns.show_duplicates)
    elif ns.console:
        return run_console(env)
    elif ns.make_config:
        return make_config(env, ns.make_config)

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
    parser.add_argument("--config", metavar="PATH", default="config.json")
    parser.add_argument("--master-password", default=None)
    parser.add_argument("-v", "--verbose", action="store_true", default=False)
    parser.add_argument("--silent", action="store_true", default=False)
    parser.add_argument("--n-workers", "-w", type=positive_int, default=1)
    parser.add_argument("-s", "--scan", default=None, nargs="+")
    parser.add_argument("-d", "--show-diffs", default=None, nargs=2)
    parser.add_argument("-S", "--sync", default=None, nargs=2)
    parser.add_argument("-D", "--download", default=None, nargs="+")
    parser.add_argument("--local-prefix", default=None)
    parser.add_argument("--remote-prefix", default=None)
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--encrypt", default=None, nargs="+")
    parser.add_argument("--decrypt", default=None, nargs="+")
    parser.add_argument("--encrypt-filename", default=None, nargs="+")
    parser.add_argument("--decrypt-filename", default=None, nargs="+")
    parser.add_argument("--encrypt-config", default=None, nargs="+")
    parser.add_argument("--decrypt-config", default=None, nargs="+")
    parser.add_argument("--show-duplicates", default=None, nargs="+")
    parser.add_argument("--console", default=False, action="store_true")
    parser.add_argument("--make-config", default=None)

    return parser.parse_args(args[1:])

if __name__ == "__main__":
    sys.exit(main(sys.argv))
