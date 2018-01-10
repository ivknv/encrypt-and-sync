#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import traceback

from yadisk.exceptions import YaDiskError

from ..Scanner import Scanner
from ..Event.EventHandler import EventHandler
from ..FileList import FileList, DuplicateList
from ..ExceptionManager import ExceptionManager
from .SignalManagers import GenericSignalManager
from .parse_choice import interpret_choice

from . import common
from .common import show_error

PRINT_RATE_LIMIT = 1.0

def ask_target_choice(targets):
    for i, target in enumerate(targets):
        print("[%d] [%s:%s]" % (i + 1, target.name, target.type))

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
    if target.storage.name == "yadisk":
        return "disk://" + target.path

    return target.path

def print_target_totals(env, target):
    n_files = n_dirs = 0

    filelist = FileList(target.name, target.storage.name, env["db_dir"])
    children = filelist.find_node_children(target.path)

    for i in children:
        if i["type"] == "f":
            n_files += 1
        elif i["type"] == "d":
            n_dirs += 1

    filelist.close()

    print("[%s:%s]: %d files" % (target.name, target.type, n_files))
    print("[%s:%s]: %d directories" % (target.name, target.type, n_dirs))

    if not target.encrypted:
        return

    duplist = DuplicateList(target.storage.name, env["db_dir"])
    duplist.create()

    children = duplist.find_children(target.path)
    n_duplicates = sum(1 for i in children)

    duplist.close()

    print("[%s:%s]: %d duplicate(s)" % (target.name, target.type, n_duplicates))

class ScannerReceiver(EventHandler):
    def __init__(self, env, scanner):
        EventHandler.__init__(self)

        self.worker_receiver = WorkerReceiver()
        self.target_receiver = TargetReceiver(env)

        self.add_emitter_callback(scanner, "started", self.on_started)
        self.add_emitter_callback(scanner, "finished", self.on_finished)
        self.add_emitter_callback(scanner, "next_target", self.on_next_target)
        self.add_emitter_callback(scanner, "worker_starting", self.on_worker_starting)
        self.add_emitter_callback(scanner, "error", self.on_error)

        self.exc_manager = ExceptionManager()

        self.exc_manager.add(YaDiskError, self.on_disk_error)
        self.exc_manager.add(BaseException, self.on_exception)

    def on_started(self, event):
        print("Scanner: started")

    def on_finished(self, event):
        print("Scanner: finished")

    def on_next_target(self, event, target):
        target.add_receiver(self.target_receiver)

        print("Performing %s scan: [%s:%s]" % (target.storage.name, target.name, target.type))

    def on_worker_starting(self, event, worker):
        worker.add_receiver(self.worker_receiver)

    def on_error(self, event, exception):
        self.exc_manager.handle(exception, event.emitter)

    def on_disk_error(self, exc, scanner):
        target = scanner.cur_target

        print("[%s:%s]: error: %s: %s" % (target.name, target.type,
                                          exc.error_type, exc))

    def on_exception(self, exc, scanner):
        traceback.print_exc()

class TargetReceiver(EventHandler):
    def __init__(self, env):
        EventHandler.__init__(self)

        self.env = env

        self.add_callback("status_changed", self.on_status_changed)
        self.add_callback("duplicates_found", self.on_duplicates_found)

    def on_status_changed(self, event):
        target = event["emitter"]

        if target.status != "pending":
            print("[%s:%s]: %s scan %s" % (target.name, target.type,
                                           target.storage.name, target.status))

        if target.status == "finished":
            print_target_totals(self.env, target)

    def on_duplicates_found(self, event, duplicates):
        print("Found %d duplicate(s) of %s" % (len(duplicates) - 1, duplicates[0].path))

class WorkerReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.add_callback("next_node", self.on_next_node)
        self.add_callback("error", self.on_error)

        self.exc_manager = ExceptionManager()

        self.exc_manager.add(YaDiskError, self.on_disk_error)
        self.exc_manager.add(BaseException, self.on_exception)

        self.last_print = 0

    def on_next_node(self, event, scannable):
        if time.time() - self.last_print < PRINT_RATE_LIMIT:
            return

        self.last_print = time.time()

        print(scannable.path)

    def on_error(self, event, exception):
        self.exc_manager.handle(exception, event.emitter)

    def on_disk_error(self, exc, scanner):
        target = scanner.cur_target

        print("[%s:%s]: error: %s: %s" % (target.name, target.type,
                                          exc.error_type, exc))

    def on_exception(self, exc, scanner):
        traceback.print_exc()

def do_scan(env, names):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    common.cleanup_filelists(env)

    n_workers = env.get("n_workers", encsync.scan_threads)
    ask = env.get("ask", False)
    choose_targets = env.get("choose_targets", False)

    names = list(names)

    if env.get("all", False):
        for name in sorted(encsync.targets.keys()):
            if not env.get("dst_only", False):
                names.append(name + ":src")

            if not env.get("src_only", False):
                names.append(name + ":dst")

    if len(names) == 0:
        show_error("Error: no targets given")
        return 1

    no_journal = env.get("no_journal", False)

    scanner = Scanner(env["encsync"], env["db_dir"], n_workers,
                      enable_journal=not no_journal)

    with GenericSignalManager(scanner):
        targets = []

        for name in names:
            if name.endswith(":src"):
                scan_type = "src"
                name = name[:-4]
            elif name.endswith(":dst"):
                scan_type = "dst"
                name = name[:-4]
            else:
                scan_type = None

            if scan_type is None:
                if env["src_only"]:
                    scan_type = "src"
                elif env["dst_only"]:
                    scan_type = "dst"

            try:
                if scan_type in (None, "src"):
                    targets.append(scanner.make_target("src", name))

                if scan_type in (None, "dst"):
                    targets.append(scanner.make_target("dst", name))
            except ValueError:
                show_error("Error: unknown target %r" % (name,))
                return 1

        if (ask and env.get("all", False)) or choose_targets:
            targets = ask_target_choice(targets)

        for target in targets:
            scanner.add_target(target)

        print("Targets to scan:")
        for target in targets:
            print("[%s:%s]" % (target.name, target.type))

        scanner_receiver = ScannerReceiver(env, scanner)

        scanner.add_receiver(scanner_receiver)

        scanner.start()
        scanner.join()

        if any(i.status not in ("finished", "skipped") for i in targets):
            return 1

        if scanner.stopped:
            return 1

        return 0
