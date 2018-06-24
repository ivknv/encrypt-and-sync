#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys

import portalocker

from .cli import common
from .cli.environment import Environment
from .cli.scan import do_scan
from .cli.show_diffs import show_diffs
from .cli.sync import do_sync
from .cli.download import download
from .cli.remove_duplicates import remove_duplicates
from .cli.encrypt import encrypt, encrypt_path
from .cli.decrypt import decrypt, decrypt_path
from .cli.show_duplicates import show_duplicates
from .cli.generate_config import generate_config
from .cli.generate_encrypted_data import generate_encrypted_data
from .cli.console import run_console
from .cli.execute import execute, execute_script
from .cli.set_key import set_key
from .cli.get_key import get_key
from .cli.set_master_password import set_master_password
from .cli.password_prompt import password_prompt
from .cli.configure import configure
from .cli.logout import logout
from .cli.authenticate_storages import authenticate_storages

from . import __version__ as EAS_VERSION

def any_not_none(keys, container):
    for key in keys:
        if getattr(container, key) is not None:
            return True

    return False

def setup_logging(env):
    import logging
    from . import downloader, synchronizer, scanner, duplicate_remover, cdb

    loggers = ((downloader.logging.logger, "downloader.log"),
               (synchronizer.logging.logger, "synchronizer.log"),
               (synchronizer.logging.fail_logger, "synchronizer-fails.log"),
               (scanner.logging.logger, "scanner.log"),
               (duplicate_remover.logging.logger, "duplicate-remover.log"),
               (cdb.logging.logger, "cdb.log"))

    for logger, filename in loggers:
        formatter = logging.Formatter("%(asctime)s - %(name)s-Thread-%(thread)d: %(message)s")

        path = os.path.join(env["log_dir"], filename)

        handler = logging.FileHandler(path)
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)

        logger.addHandler(handler)

def main(args=None):
    if args is None:
        args = sys.argv

    parser, ns = parse_args(args)

    if ns.version:
        print("Encrypt & Sync %s" % (EAS_VERSION,))
        return 0

    if getattr(ns, "action", None) is None:
        parser.print_help()
        return 1

    # Top-level environment
    genv = Environment()
    genv["force_ask_password"] = ns.force_ask_password
    
    if ns.master_password is None and not ns.force_ask_password and ns.action != "password_prompt":
        try:
            genv["master_password"] = os.environ["EAS_MASTER_PASSWORD"]
        except KeyError:
            pass
    else:
        genv["master_password"] = ns.master_password

    if ns.config_dir is not None or genv.get("config_dir") is None:
        if ns.config_dir is None:
            ns.config_dir = "~/.eas"

        genv["config_dir"] = os.path.abspath(os.path.expanduser(ns.config_dir))
        genv["db_dir"] = os.path.join(genv["config_dir"], "databases")
        genv["log_dir"] = os.path.join(genv["config_dir"], "logs")
        genv["lockfile_path"] = os.path.join(genv["config_dir"], ".lockfile")
        genv["config_path"] = os.path.join(genv["config_dir"], "eas.conf")
        genv["enc_data_path"] = os.path.join(genv["config_dir"], "encrypted_data.json")

    common.create_eas_dirs(genv)

    if not os.path.exists(genv["config_path"]):
        generate_config(genv, genv["config_path"])

    if not os.path.exists(genv["enc_data_path"]):
        generate_encrypted_data(genv, genv["enc_data_path"])

    setup_logging(genv)

    env = Environment(genv)

    env["ask"] = not getattr(ns, "no_ask", False)

    if ns.action == "sync":
        env["no_check"] = not ns.integrity_check
        env["no_scan"] = ns.no_scan
        env["no_diffs"] = ns.no_diffs
        env["no_remove"] = ns.no_remove
        env["no_sync_modified"] = ns.no_sync_modified
        env["no_sync_mode"] = ns.no_sync_mode
        env["sync_ownership"] = ns.sync_ownership
        env["force_scan"] = ns.force_scan
    elif ns.action == "download":
        env["no_skip"] = ns.no_skip
    elif ns.action == "rmdup":
        env["no_preserve_modified"] = ns.no_preserve_modified

    if ns.action in ("scan", "sync", "download", "rmdup"):
        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        env["no_progress"] = ns.no_progress

    if ns.action in ("scan", "sync", "rmdup"):
        env["all"] = ns.all
        env["choose_targets"] = ns.choose_targets
        env["no_journal"] = ns.no_journal

    if ns.action in ("scan", "sync", "rmdup", "download", "login", "logout",
                     "console", "execute", "execute_script"):
        env["no_auth_check"] = ns.no_auth_check

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
               "configure": lambda: configure(env),
               "logout": lambda: logout(env, ns.storages),
               "login": lambda: authenticate_storages(env, ns.storages or None)}

    try:
        common.cleanup(genv)
    except portalocker.exceptions.AlreadyLocked:
        pass

    ret = actions[ns.action]()

    try:
        common.cleanup(genv)
    except portalocker.exceptions.AlreadyLocked:
        pass

    return ret

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

    parser.add_argument("-V", "--version", action="store_true",
                        help="Print Encrypt & Sync version number and exit")

    subparsers = parser.add_subparsers(title="Actions", metavar="<action>")
    global_group = parser.add_argument_group("Global options")
    global_group.add_argument("--master-password", default=None, metavar="PASSWORD",
                              help="Master password to use")
    global_group.add_argument("--force-ask-password", action="store_true",
                              help="Always ask for master password")
    global_group.add_argument("--config-dir", metavar="PATH", default=None,
                              help="Path to the configuration directory")

    scan_parser = subparsers.add_parser("scan", aliases=["s"], help="Scan folders/paths")
    scan_parser.add_argument("folders", nargs="*", help="List of folders/paths to scan")
    scan_parser.add_argument("-a", "--all", action="store_true",
                             help="Scan all folders")
    scan_parser.add_argument("--ask", action="store_true", help="(deprecated)")
    scan_parser.add_argument("--no-ask", action="store_true",
                             help="Don't ask for any user input")
    scan_parser.add_argument("--choose-targets", action="store_true",
                             help="Choose which folders to scan")
    scan_parser.add_argument("--no-journal", action="store_true",
                             help="Disable SQLite3 journaling")
    scan_parser.add_argument("--no-auth-check", action="store_true",
                             help="Disable the authentication check")
    scan_parser.add_argument("--no-progress", action="store_true",
                             help="Don't show intermediate progress")
    scan_parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                             help="Number of workers to use")
    scan_parser.set_defaults(action="scan")

    diffs_parser = subparsers.add_parser("diffs", aliases=["differences"],
                                         help="Show differences between directories")
    diffs_parser.add_argument("folders", nargs=2, help="Folders to show differences for")
    diffs_parser.set_defaults(func=show_diffs, action="diffs")

    sync_parser = subparsers.add_parser("sync", aliases=["S"], help="Sync targets")
    sync_parser.add_argument("folders", nargs="*", help="List of folders/paths to sync")
    sync_parser.add_argument("-I", "--integrity-check", action="store_true",
                             help="Enable integrity check")
    sync_parser.add_argument("--no-scan", action="store_true", help="Disable scan")
    sync_parser.add_argument("--no-diffs", action="store_true",
                             help="Don't show the list of differences")
    sync_parser.add_argument("-a", "--all", action="store_true",
                             help="Sync all targets")
    sync_parser.add_argument("--ask", action="store_true", help="(deprecated)")
    sync_parser.add_argument("--sync-ownership", action="store_true",
                             help="Sync ownership of files")
    sync_parser.add_argument("--force-scan", action="store_true",
                             help="Always scan everything")
    sync_parser.add_argument("--no-ask", action="store_true",
                             help="Don't ask for any user input")
    sync_parser.add_argument("--choose-targets", action="store_true",
                             help="Choose which targets to sync")
    sync_parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                             help="Number of workers to use")
    sync_parser.add_argument("--no-sync-modified", action="store_true",
                             help="Don't try to sync modified date for files")
    sync_parser.add_argument("--no-sync-mode", action="store_true",
                             help="Don't try to sync file mode (permissions, owner, group, etc.)")
    sync_parser.add_argument("--no-journal", action="store_true",
                             help="Disable SQLite3 journaling")
    sync_parser.add_argument("--no-auth-check", action="store_true",
                             help="Disable the authentication check")
    sync_parser.add_argument("--no-remove", action="store_true",
                             help="Don't remove any files (except for file duplicates)")
    sync_parser.add_argument("--no-progress", action="store_true",
                             help="Don't show intermediate progress")
    sync_parser.set_defaults(action="sync")
    
    download_parser = subparsers.add_parser("download", aliases=["d"],
                                            help="Download files/directories")
    download_parser.add_argument("paths", nargs="+", help="List of paths to download")
    download_parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                                 help="Number of workers to use")
    download_parser.add_argument("--no-ask", action="store_true",
                                 help="Don't ask for any user input")
    download_parser.add_argument("--no-auth-check", action="store_true",
                                 help="Disable the authentication check")
    download_parser.add_argument("--no-progress", action="store_true",
                                 help="Don't show intermediate progress")
    download_parser.add_argument("--no-skip", action="store_true",
                                 help="Don't skip already downloaded files")
    download_parser.set_defaults(action="download")
    
    rmdup_parser = subparsers.add_parser("rmdup", aliases=["remove-duplicates"],
                                         help="Remove duplicates")
    rmdup_parser.add_argument("paths", nargs="*", help="pathm to remove duplicates from")
    rmdup_parser.add_argument("-a", "--all", action="store_true",
                              help="Remove duplicates from all folders")
    rmdup_parser.add_argument("--ask", action="store_true", help="(deprecated)")
    rmdup_parser.add_argument("--no-ask", action="store_true",
                             help="Don't ask for any user input")
    rmdup_parser.add_argument("--choose-targets", action="store_true",
                              help="Choose which folders to remove duplicates for")
    rmdup_parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                              help="Number of workers to use")
    rmdup_parser.add_argument("--no-preserve-modified", action="store_true",
                              help="Don't try to preserve modified date of directories")
    rmdup_parser.add_argument("--no-journal", action="store_true",
                              help="Disable SQLite3 journaling")
    rmdup_parser.add_argument("--no-auth-check", action="store_true",
                              help="Disable the authentication check")
    rmdup_parser.add_argument("--no-progress", action="store_true",
                              help="Don't show intermediate progress")
    rmdup_parser.set_defaults(action="rmdup")
    
    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt files")
    encrypt_parser.add_argument("paths", nargs="+", help="List of files to encrypt")
    encrypt_parser.add_argument("--no-ask", action="store_true",
                                help="Don't ask for any user input")
    encrypt_parser.set_defaults(action="encrypt")

    decrypt_parser = subparsers.add_parser("decrypt", help="Decrypt files")
    decrypt_parser.add_argument("paths", nargs="+", help="List of files to decrypt")
    decrypt_parser.add_argument("--no-ask", action="store_true",
                                help="Don't ask for any user input")
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
    encrypt_path_parser.add_argument("--no-ask", action="store_true",
                                     help="Don't ask for any user input")
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
    decrypt_path_parser.add_argument("--no-ask", action="store_true",
                                     help="Don't ask for any user input")
    decrypt_path_parser.set_defaults(action="decrypt_path")

    duplicates_parser = subparsers.add_parser("duplicates", help="Show duplicates")
    duplicates_parser.add_argument("paths", nargs="+",
                                   help="List of paths to show duplicates for")
    duplicates_parser.set_defaults(action="duplicates")
    
    console_parser = subparsers.add_parser("console", help="Run console")
    console_parser.add_argument("--no-auth-check", action="store_true",
                                help="Disable the authentication check")
    console_parser.add_argument("--no-ask", action="store_true",
                                help="Don't ask for any user input")
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
    get_key_parser.add_argument("--no-ask", action="store_true",
                             help="Don't ask for any user input")
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

    login_parser = subparsers.add_parser("login",
                                         help="Log into a storage")
    login_parser.add_argument("storages", nargs="*",
                              help="List of storage names to log into. default: all storages used in folders")
    login_parser.add_argument("--no-auth-check", action="store_true",
                              help="Disable the authentication check")
    login_parser.add_argument("--no-ask", action="store_true",
                              help="Don't ask for any user input")
    login_parser.set_defaults(action="login")

    logout_parser = subparsers.add_parser("logout",
                                          help="Log out of a storage")
    logout_parser.add_argument("storages", nargs="*",
                               help="List of storage names to logout from. default: all storages")
    logout_parser.add_argument("--no-auth-check", action="store_true",
                               help="Disable the authentication check")
    logout_parser.set_defaults(action="logout")

    ns = parser.parse_args(args[1:])

    return parser, ns

if __name__ == "__main__":
    sys.exit(main(sys.argv))
