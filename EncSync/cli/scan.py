#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from ..Scanner import Scanner
from ..Event.Receiver import Receiver
from ..FileList import FileList, DuplicateList
from .SignalManagers import GenericSignalManager
from .parse_choice import interpret_choice
from .authenticate_storages import authenticate_storages

from . import common
from .common import show_error

PRINT_RATE_LIMIT = 1.0

__all__ = ["do_scan", "ScannerReceiver"]

def ask_target_choice(targets):
    for i, target in enumerate(targets):
        print("[%d] [%s]" % (i + 1, target.name))

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

    filelist = FileList(target.name, env["db_dir"])
    children = filelist.find_node_children(target.path)

    for i in children:
        if i["type"] == "f":
            n_files += 1
        elif i["type"] == "d":
            n_dirs += 1

    filelist.close()

    print("[%s]: %d files" % (target.name, n_files))
    print("[%s]: %d directories" % (target.name, n_dirs))

    if not target.encrypted:
        return

    duplist = DuplicateList(target.type, env["db_dir"])
    duplist.create()

    children = duplist.find_children(target.path)
    n_duplicates = sum(1 for i in children)

    duplist.close()

    print("[%s]: %d duplicate(s)" % (target.name, n_duplicates))

class ScannerReceiver(Receiver):
    def __init__(self, env, scanner):
        Receiver.__init__(self)

        self.worker_receiver = WorkerReceiver(env)
        self.target_receiver = TargetReceiver(env)

    def on_started(self, event):
        print("Scanner: started")

    def on_finished(self, event):
        print("Scanner: finished")

    def on_next_target(self, event, target):
        target.add_receiver(self.target_receiver)

        print("Performing %s scan: [%s]" % (target.type, target.name))

    def on_worker_starting(self, event, worker):
        worker.add_receiver(self.worker_receiver)

    def on_error(self, event, exc):
        common.show_exception(exc)

class TargetReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.env = env

    def on_status_changed(self, event):
        target = event["emitter"]

        if target.status != "pending":
            print("[%s]: %s scan %s" % (target.name, target.type, target.status))

        if target.status == "finished":
            print_target_totals(self.env, target)

    def on_duplicates_found(self, event, duplicates):
        if env.get("no_progress", False):
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

        if time.time() - self.last_print < PRINT_RATE_LIMIT:
            return

        self.last_print = time.time()

        print(scannable.path)

    def on_error(self, event, exc):
        common.show_exception(exc)

def do_scan(env, names):
    config, ret = common.make_config(env)

    if config is None:
        return ret

    common.cleanup_filelists(env)

    n_workers = env.get("n_workers", config.scan_threads)
    ask = env.get("ask", False)
    choose_targets = env.get("choose_targets", False)

    names = list(names)

    if env.get("all", False):
        names += sorted(config.folders.keys())

    if len(names) == 0:
        show_error("Error: no folders given")
        return 1

    no_journal = env.get("no_journal", False)

    scanner = Scanner(env["config"], env["db_dir"], n_workers,
                      enable_journal=not no_journal)

    targets = []

    for name in names:
        try:
            targets.append(scanner.make_target(name))
        except ValueError:
            show_error("Error: unknown folder %r" % (name,))
            return 1

    if (ask and env.get("all", False)) or choose_targets:
        targets = ask_target_choice(targets)

    for target in targets:
        scanner.add_target(target)

    print("Folders to scan:")
    for target in targets:
        print("[%s]" % (target.name,))

    scanner_receiver = ScannerReceiver(env, scanner)

    scanner.add_receiver(scanner_receiver)

    ret = authenticate_storages(env, {i.type for i in targets})

    if ret:
        return ret

    with GenericSignalManager(scanner):
        scanner.start()
        scanner.join()

        if any(i.status not in ("finished", "skipped") for i in targets):
            return 1

        if scanner.stopped:
            return 1

        return 0
