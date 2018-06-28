#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time

import portalocker

from ..scanner import Scanner, ScanTarget
from ..events import Receiver
from ..filelist import Filelist
from ..duplicate_list import DuplicateList
from .generic_signal_manager import GenericSignalManager
from .parse_choice import interpret_choice
from .authenticate_storages import authenticate_storages
from ..common import Lockfile, validate_folder_name, recognize_path
from .. import pathm

from . import common
from .common import show_error

PRINT_RATE_LIMIT = 1.0

__all__ = ["do_scan", "ScannerReceiver"]

def get_target_display_name(target):
    if pathm.is_equal(target.path, target.prefix):
        return "[%s]" % (target.name,)

    path = pathm.cut_prefix(target.path, target.prefix)
    path = path.lstrip("/") or "/"

    return "[%s][%s]" % (target.name, path)

def ask_target_choice(targets):
    for i, target in enumerate(targets):
        display_name = get_target_display_name(target)

        print("[%d] %s" % (i + 1, display_name))

    while True:
        try:
            answer = input("Enter the numbers of targets [default: all]: ")
        except (KeyboardInterrupt, EOFError):
            return []

        if answer.isspace() or not answer:
            answer = "all"

        try:
            return interpret_choice(answer, targets)
        except (ValueError, IndexError) as e:
            show_error("Error: %s" % str(e))

def get_path_with_schema(target):
    if target.type == "yadisk":
        return "disk://" + target.path

    return target.path

def print_target_totals(env, target):
    n_files = n_dirs = 0

    filelist = Filelist(target.name, env["db_dir"])
    children = filelist.find_recursively(target.path)

    for i in children:
        if i["type"] == "f":
            n_files += 1
        elif i["type"] == "d":
            n_dirs += 1

    filelist.close()

    print("%s: %d files" % (get_target_display_name(target), n_files))
    print("%s: %d directories" % (get_target_display_name(target), n_dirs))

    if not target.encrypted:
        return

    duplist = DuplicateList(target.type, env["db_dir"])
    duplist.create()

    children = duplist.find_recursively(target.path)
    n_duplicates = sum(1 for i in children)

    duplist.close()

    print("%s: %d duplicate(s)" % (get_target_display_name(target), n_duplicates))

class ScannerReceiver(Receiver):
    def __init__(self, env, scanner):
        Receiver.__init__(self)

        self.target_receiver = TargetReceiver(env)

    def on_next_target(self, event, target):
        target.add_receiver(self.target_receiver)

        print("Performing %s scan: %s" % (target.type, get_target_display_name(target)))

    def on_error(self, event, exc):
        common.show_exception(exc)

class PoolReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.env = env
        self.worker_receiver = WorkerReceiver(env)

    def on_spawn(self, event, worker):
        worker.add_receiver(self.worker_receiver)

class TargetReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.env = env
        self.pool_receiver = PoolReceiver(env)

    def on_status_changed(self, event):
        target = event["emitter"]

        if target.status == "pending":
            target.pool.add_receiver(self.pool_receiver)
        else:
            print("%s: %s scan %s" % (get_target_display_name(target),
                                      target.type, target.status))

        if target.status == "finished":
            print_target_totals(self.env, target)

    def on_duplicates_found(self, event, duplicates):
        if self.env.get("no_progress", False):
            return

        print("Found %d duplicate(s) of %s" % (len(duplicates) - 1, duplicates[0].path))

class WorkerReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.env = env
        self.last_print = 0

    def on_next_node(self, event, scannable):
        if self.env.get("no_progress", False):
            return

        if time.monotonic() - self.last_print < PRINT_RATE_LIMIT:
            return

        self.last_print = time.monotonic()

        print(scannable.path)

    def on_error(self, event, exc):
        common.show_exception(exc)

def do_scan(env, names_or_paths):
    lockfile = Lockfile(env["lockfile_path"])

    try:
        lockfile.acquire()
    except portalocker.exceptions.AlreadyLocked:
        common.show_error("Error: there can be only one Encrypt & Sync (the lockfile is already locked)")
        return 1

    config, ret = common.make_config(env)

    if config is None:
        return ret

    n_workers = env.get("n_workers", config.scan_threads)
    ask = env.get("ask", False)
    choose_targets = env.get("choose_targets", False)

    names_or_paths = list(names_or_paths)

    if env.get("all", False):
        names_or_paths += sorted(config.folders.keys())

    if len(names_or_paths) == 0:
        show_error("Error: no folders or paths given")
        return 1

    no_journal = env.get("no_journal", False)

    scanner = Scanner(env["config"], env["db_dir"],
                      enable_journal=not no_journal)

    targets = []

    for name_or_path in names_or_paths:
        if validate_folder_name(name_or_path):
            try:
                folder = config.folders[name_or_path]
            except KeyError:
                show_error("Error: unknown folder %r" % (name_or_path,))
                return 1

            path_with_proto = folder["type"] + "://" + folder["path"]
        else:
            path_with_proto = name_or_path

            path, proto = recognize_path(path_with_proto)

            if proto == "local":
                path = pathm.from_sys(os.path.abspath(os.path.expanduser(path)))

            path_with_proto = proto + "://" + path

        try:
            target = ScanTarget(scanner, path_with_proto)
            target.n_workers = n_workers

            targets.append(target)
        except KeyError as e:
            show_error("Error: %s" % (e,))
            return 1

    if (ask and env.get("all", False)) or choose_targets:
        targets = ask_target_choice(targets)

    for target in targets:
        scanner.add_target(target)

    print("Folders to scan:")
    for target in targets:
        print(get_target_display_name(target))

    scanner_receiver = ScannerReceiver(env, scanner)

    scanner.add_receiver(scanner_receiver)

    ret = authenticate_storages(env, {i.type for i in targets})

    if ret:
        return ret

    with GenericSignalManager(scanner):
        print("Scanner: starting")

        # This contraption is needed to silence a SystemExit traceback
        # The traceback would be printed otherwise due to use of a finally clause
        try:
            try:
                scanner.run()
            finally:
                print("Scanner: finished")
        except SystemExit as e:
            sys.exit(e.code)

    if any(i.status not in ("finished", "skipped") for i in targets):
        return 1

    if scanner.stopped:
        return 1

    return 0
