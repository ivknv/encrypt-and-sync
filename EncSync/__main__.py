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
from .cli.remove_duplicates import remove_duplicates
from .cli.authenticate_storages import authenticate_storages
from .cli.encrypt import encrypt, encrypt_path
from .cli.decrypt import decrypt, decrypt_path
from .cli.show_duplicates import show_duplicates
from .cli.generate_config import generate_config
from .cli.generate_encrypted_data import generate_encrypted_data
from .cli.Console import run_console
from .cli.execute import execute, execute_script
from .cli.set_key import set_key
from .cli.get_key import get_key
from .cli.set_master_password import set_master_password
from .cli.password_prompt import password_prompt
from .cli.configure import configure

def cleanup(env):
    try:
        os.remove(os.path.join(env["db_dir"], "encsync_diffs.db"))
    except (FileNotFoundError, IsADirectoryError):
        pass

def any_not_none(keys, container):
    for key in keys:
        if getattr(container, key) is not None:
            return True

    return False

def setup_logging(env):
    import logging
    from . import Downloader, Synchronizer, Scanner, DuplicateRemover, CDB

    loggers = ((Downloader.Logging.logger, "downloader.log"),
               (Synchronizer.Logging.logger, "synchronizer.log"),
               (Scanner.Logging.logger, "scanner.log"),
               (DuplicateRemover.Logging.logger, "duplicate-remover.log"),
               (CDB.Logging.logger, "cdb.log"))

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

    parser, ns = parse_args(args)

    if getattr(ns, "action", None) is None:
        parser.print_help()
        return 1

    # Top-level environment
    genv = Environment()
    
    if ns.master_password is None and not ns.force_ask_password and ns.action != "password_prompt":
        try:
            genv["master_password"] = os.environ["ENCSYNC_MASTER_PASSWORD"]
        except KeyError:
            pass
    else:
        genv["master_password"] = ns.master_password

    if ns.config_dir is not None or genv.get("config_dir", None) is None:
        if ns.config_dir is None:
            ns.config_dir = "~/.encsync"

        genv["config_dir"] = os.path.realpath(os.path.expanduser(ns.config_dir))
        genv["db_dir"] = os.path.join(genv["config_dir"], "databases")
        genv["config_path"] = os.path.join(genv["config_dir"], "encsync.conf")
        genv["enc_data_path"] = os.path.join(genv["config_dir"], "encrypted_data.json")

    common.create_encsync_dirs(genv)

    if not os.path.exists(genv["config_path"]):
        generate_config(genv, genv["config_path"])

    if not os.path.exists(genv["enc_data_path"]):
        generate_encrypted_data(genv, genv["enc_data_path"])

    setup_logging(genv)

    cleanup(genv)

    requiring_auth = {"scan", "sync", "download", "console", "rmdup"}

    env = Environment(genv)

    if ns.action in requiring_auth:
        env["no_auth_check"] = ns.no_auth_check
        ret = authenticate_storages(env)

        if ret:
            return ret

    if ns.action == "sync":
        env["no_check"] = not ns.integrity_check
        env["no_scan"] = ns.no_scan
        env["no_diffs"] = ns.no_diffs

    if ns.action in ("scan", "sync", "download", "rmdup"):
        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

    if ns.action in ("scan", "sync", "rmdup"):
        env["all"] = ns.all
        env["ask"] = ns.ask
        env["choose_targets"] = ns.choose_targets
        env["no_journal"] = ns.no_journal

    if ns.action in ("scan", "rmdup"):
        env["src_only"] = ns.src_only
        env["dst_only"] = ns.dst_only

    actions = {"scan": lambda: do_scan(env, ns.folders),
               "sync": lambda: do_sync(env, ns.folders),
               "diffs": lambda: show_diffs(env, *ns.folders[:2]),
               "download": lambda: download(env, ns.paths),
               "rmdup": lambda: remove_duplicates(env, ns.paths),
               "encrypt": lambda: encrypt(env, ns.paths),
               "encrypt_path": lambda: encrypt_path(env,
                                                    ns.paths,
                                                    ns.prefix,
                                                    ns.filename_encoding),
               "decrypt": lambda: decrypt(env, ns.paths),
               "decrypt_path": lambda: decrypt_path(env,
                                                    ns.paths,
                                                    ns.prefix,
                                                    ns.filename_encoding),
               "duplicates": lambda: show_duplicates(env, ns.paths),
               "console": lambda: run_console(env),
               "make_config": lambda: generate_config(env, ns.path),
               "execute": lambda: execute(env, ns.expression),
               "execute_script": lambda: execute_script(env, ns.script),
               "set_key": lambda: set_key(env),
               "get_key": lambda: get_key(env),
               "set_master_password": lambda: set_master_password(env),
               "password_prompt": lambda: password_prompt(env),
               "configure": lambda: configure(env)}

    return actions[ns.action]()

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

    subparsers = parser.add_subparsers(title="Actions", metavar="<action>")
    global_group = parser.add_argument_group("Global options")
    global_group.add_argument("--master-password", default=None, metavar="PASSWORD",
                              help="Master password to use")
    global_group.add_argument("--force-ask-password", action="store_true",
                              help="Always ask for master password")
    global_group.add_argument("--config-dir", metavar="PATH", default=None,
                              help="Path to the configuration directory")

    scan_parser = subparsers.add_parser("scan", aliases=["s"], help="Scan targets")
    scan_parser.add_argument("folders", nargs="*", help="List of targets to scan")
    group1 = scan_parser.add_mutually_exclusive_group()
    group1.add_argument("--src-only", action="store_true",
                        help="Scan only source paths")
    group1.add_argument("--dst-only", action="store_true",
                        help="Scan only destination paths")
    scan_parser.add_argument("-a", "--all", action="store_true",
                             help="Scan all targets")
    scan_parser.add_argument("--ask", action="store_true",
                             help="Ask for user's action in certain cases")
    scan_parser.add_argument("--choose-targets", action="store_true",
                             help="Choose which targets to scan")
    scan_parser.add_argument("--no-journal", action="store_true",
                             help="Disable SQLite3 journaling")
    scan_parser.add_argument("--no-auth-check", action="store_true",
                             help="Disable the authentication check")
    scan_parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                             help="Number of workers to use")
    scan_parser.set_defaults(action="scan")

    diffs_parser = subparsers.add_parser("diffs", aliases=["differences"],
                                         help="Show differences between directories")
    diffs_parser.add_argument("folders", nargs=2, help="Folders to show differences for")
    diffs_parser.set_defaults(func=show_diffs, action="diffs")

    sync_parser = subparsers.add_parser("sync", aliases=["S"], help="Sync targets")
    sync_parser.add_argument("folders", nargs="*", help="List of folders to sync")
    sync_parser.add_argument("-I", "--integrity-check", action="store_true",
                             help="Enable integrity check")
    sync_parser.add_argument("--no-scan", action="store_true", help="Disable scan")
    sync_parser.add_argument("--no-diffs", action="store_true",
                             help="Don't show the list of differences")
    sync_parser.add_argument("-a", "--all", action="store_true",
                             help="Sync all targets")
    sync_parser.add_argument("--ask", action="store_true",
                             help="Ask for user's action in certain cases")
    sync_parser.add_argument("--choose-targets", action="store_true",
                             help="Choose which targets to sync")
    sync_parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                             help="Number of workers to use")
    sync_parser.add_argument("--no-journal", action="store_true",
                             help="Disable SQLite3 journaling")
    sync_parser.add_argument("--no-auth-check", action="store_true",
                             help="Disable the authentication check")
    sync_parser.set_defaults(action="sync")
    
    download_parser = subparsers.add_parser("download", aliases=["d"],
                                            help="Download files/directories")
    download_parser.add_argument("paths", nargs="+", help="List of paths to download")
    download_parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                                 help="Number of workers to use")
    download_parser.add_argument("--no-auth-check", action="store_true",
                                 help="Disable the authentication check")
    download_parser.set_defaults(action="download")
    
    rmdup_parser = subparsers.add_parser("rmdup", aliases=["remove-duplicates"],
                                         help="Remove duplicates")
    rmdup_parser.add_argument("paths", nargs="*", help="Paths to remove duplicates from")
    rmdup_parser.add_argument("-a", "--all", action="store_true",
                              help="Remove duplicates from all targets")
    rmdup_parser.add_argument("--ask", action="store_true",
                              help="Ask for user's action in certain cases")
    group2 = rmdup_parser.add_mutually_exclusive_group()
    group2.add_argument("--src-only", action="store_true",
                        help="Remove duplicates only from source paths")
    group2.add_argument("--dst-only", action="store_true",
                        help="Remove duplicates only from destination paths")
    rmdup_parser.add_argument("--choose-targets", action="store_true",
                              help="Choose which targets to remove duplicates for")
    rmdup_parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                              help="Number of workers to use")
    rmdup_parser.add_argument("--no-journal", action="store_true",
                              help="Disable SQLite3 journaling")
    rmdup_parser.add_argument("--no-auth-check", action="store_true",
                              help="Disable the authentication check")
    rmdup_parser.set_defaults(action="rmdup")
    
    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt files")
    encrypt_parser.add_argument("paths", nargs="+", help="List of files to encrypt")
    encrypt_parser.set_defaults(action="encrypt")

    decrypt_parser = subparsers.add_parser("decrypt", help="Decrypt files")
    decrypt_parser.add_argument("paths", nargs="+", help="List of files to decrypt")
    decrypt_parser.set_defaults(action="decrypt")
    
    encrypt_path_parser = subparsers.add_parser("encrypt-path",
                                                help="Encrypt paths")
    encrypt_path_parser.add_argument("paths", nargs="+",
                                     help="List of paths to encrypt")
    encrypt_path_parser.add_argument("-e", "--filename-encoding", default="base64",
                                     choices=["base64", "base41"],
                                     help="Filename encoding to use")
    encrypt_path_parser.add_argument("-p", "--prefix", default="/",
                                     help="Path prefix to keep unencrypted")
    encrypt_path_parser.set_defaults(action="encrypt_path")

    decrypt_path_parser = subparsers.add_parser("decrypt-path",
                                                help="Decrypt paths")
    decrypt_path_parser.add_argument("paths", nargs="+",
                                     help="List of paths to decrypt")
    decrypt_path_parser.add_argument("-e", "--filename-encoding", default="base64",
                                     choices=["base64", "base41"],
                                     help="Filename encoding to use")
    decrypt_path_parser.add_argument("-p", "--prefix", default="/",
                                     help="Path prefix to keep as is")
    decrypt_path_parser.set_defaults(action="decrypt_path")

    duplicates_parser = subparsers.add_parser("duplicates", help="Show duplicates")
    duplicates_parser.add_argument("paths", nargs="+",
                                   help="List of paths to show duplicates for")
    duplicates_parser.set_defaults(action="duplicates")
    
    console_parser = subparsers.add_parser("console", help="Run console")
    console_parser.add_argument("--no-auth-check", action="store_true",
                                help="Disable the authentication check")
    console_parser.set_defaults(action="console")
    
    make_config_parser = subparsers.add_parser("make-config",
                                               help="Make a template config")
    make_config_parser.add_argument("path", help="Path to the new configuration")
    make_config_parser.set_defaults(action="make_config")

    execute_parser = subparsers.add_parser("execute", aliases=["exec"],
                                           help="Execute a console command")
    execute_parser.add_argument("expression", help="Expression to execute")
    execute_parser.add_argument("--no-auth-check", action="store_true",
                                help="Disable the authentication check")
    execute_parser.set_defaults(action="execute")
    
    execute_script_parser = subparsers.add_parser("execute-script", aliases=["exec-script"],
                                                  help="Execute a console script")
    execute_script_parser.add_argument("script", help="Path to the script to execute")
    execute_script_parser.add_argument("--no-auth-check", action="store_true",
                                       help="Disable the authentication check")
    execute_script_parser.set_defaults(action="execute_script")
    
    set_key_parser = subparsers.add_parser("set-key", help="Set encryption key")
    set_key_parser.set_defaults(action="set_key")

    get_key_parser = subparsers.add_parser("get-key", help="Get encryption key")
    get_key_parser.set_defaults(action="get_key")

    set_master_password_parser = subparsers.add_parser("set-master-password",
                                                       aliases=["set-password"],
                                                       help="Set the master password")
    set_master_password_parser.set_defaults(action="set_master_password")

    password_prompt_parser = subparsers.add_parser("password-prompt",
                                                   help="Run the password prompt and print the password")
    password_prompt_parser.set_defaults(action="password_prompt")

    configure_parser = subparsers.add_parser("configure",
                                             help="Quick start and interactive configuration")
    configure_parser.set_defaults(action="configure")


    ns = parser.parse_args(args[1:])

    return parser, ns

if __name__ == "__main__":
    sys.exit(main(sys.argv))
