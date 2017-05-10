#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse

from .cli import common
from .cli.scan import do_scan
from .cli.show_diffs import show_diffs
from .cli.sync import do_sync
from .cli.download import download
from .cli.check_token import check_token
from .cli.encrypt import encrypt, encrypt_config, encrypt_filename
from .cli.decrypt import decrypt, decrypt_config, decrypt_filename
from .cli.show_duplicates import show_duplicates
from .cli.Console import run_console

global_vars = common.global_vars

def main(ns):
    global_vars["verbose"] = ns.verbose
    global_vars["n_workers"] = ns.n_workers
    global_vars["master_password"] = ns.master_password
    global_vars["config"] = ns.config
    global_vars["local_prefix"] = ns.local_prefix
    global_vars["remote_prefix"] = ns.remote_prefix

    if ns.scan or ns.show_diffs or ns.sync or ns.download:
        check_token()

    if ns.scan is not None:
        do_scan(ns.scan)
    elif ns.show_diffs is not None:
        show_diffs(*ns.show_diffs[:2])
    elif ns.sync is not None:
        do_sync(ns.sync)
    elif ns.download is not None:
        download(ns.download)
    elif ns.encrypt is not None:
        encrypt(ns.encrypt)
    elif ns.decrypt is not None:
        decrypt(ns.decrypt)
    elif ns.encrypt_filename is not None:
        encrypt_filename(ns.encrypt_filename, ns.prefix or "/")
    elif ns.decrypt_filename is not None:
        decrypt_filename(ns.decrypt_filename, ns.prefix or "/")
    elif ns.encrypt_config is not None:
        in_path = ns.encrypt_config[0]
        try:
            out_path = ns.encrypt_config[1]
        except IndexError:
            out_path = in_path
        encrypt_config(in_path, out_path)
    elif ns.decrypt_config is not None:
        in_path = ns.decrypt_config[0]
        try:
            out_path = ns.decrypt_config[1]
        except IndexError:
            out_path = in_path
        decrypt_config(in_path, out_path)
    elif ns.show_duplicates is not None:
        show_duplicates(ns.show_duplicates)
    elif ns.console:
        run_console()

def positive_int(arg):
    try:
        n = int(arg)
        if n > 0:
            return n
    except ValueError:
        pass

    raise argparse.ArgumentTypeError("%r is not a positive integer" % arg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronizes encrypted files")
    parser.add_argument("--config", metavar="PATH", default="config.json")
    parser.add_argument("--master-password", default=None)
    parser.add_argument("-v", "--verbose", action="store_true", default=False)
    parser.add_argument("--silent", action="store_true", default=False)
    parser.add_argument("--n-workers", type=positive_int, default=1)
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

    main(parser.parse_args(sys.argv[1:]))
