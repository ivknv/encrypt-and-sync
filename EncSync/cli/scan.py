#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import traceback

from yadisk.exceptions import YaDiskError

from ..Scanner import Scanner, ScanTarget
from ..Event.EventHandler import EventHandler
from ..FileList import LocalFileList, RemoteFileList, DuplicateList
from .. import Paths
from .SignalManagers import GenericSignalManager
from .parse_choice import interpret_choice
from ..ExceptionManager import ExceptionManager

from . import common
from .common import show_error

PRINT_RATE_LIMIT = 1.0

def ask_target_choice(targets):
    for i, target in enumerate(targets):
        path = get_path_with_schema(target)
        print("[%d] [%s]" % (i + 1, path))

    while True:
        try:
            answer = input("Enter numbers of targets [default: all]: ")
        except (KeyboardInterrupt, EOFError):
            return []

        if answer.isspace() or not answer:
            answer = "all"

        try:
            return interpret_choice(answer, targets)
        except (ValueError, IndexError) as e:
            print("Error: %s" % str(e))

def get_path_with_schema(target):
    if target.type == "remote":
        return "disk://" + target.path

    return target.path

def print_target_totals(env, target):
    n_files = n_dirs = 0

    assert(target.type in ("local", "remote"))

    if target.type == "local":
        filelist = LocalFileList(target.name, env["db_dir"])
        children = filelist.find_node_children(Paths.from_sys(target.path))
    elif target.type == "remote":
        filelist = RemoteFileList(target.name, env["db_dir"])
        children = filelist.find_node_children(target.path)

    for i in children:
        if i["type"] == "f":
            n_files += 1
        elif i["type"] == "d":
            n_dirs += 1

    filelist.close()

    path = get_path_with_schema(target)

    print("[%s]: %d files" % (path, n_files))
    print("[%s]: %d directories" % (path, n_dirs))

    if target.type != "remote":
        return

    duplist = DuplicateList(env["db_dir"])
    duplist.create()

    children = duplist.find_children(target.path)
    n_duplicates = sum(1 for i in children)

    duplist.close()

    print("[%s]: %d duplicates" % (path, n_duplicates))

class ScannerReceiver(EventHandler):
    def __init__(self, scanner):
        EventHandler.__init__(self)

        self.worker_receiver = WorkerReceiver()

        self.add_emitter_callback(scanner, "started", self.on_started)
        self.add_emitter_callback(scanner, "finished", self.on_finished)
        self.add_emitter_callback(scanner, "next_target", self.on_next_target)
        self.add_emitter_callback(scanner, "worker_started", self.on_worker_started)
        self.add_emitter_callback(scanner, "error", self.on_error)

        self.exc_manager = ExceptionManager()

        self.exc_manager.add(YaDiskError, self.on_disk_error)
        self.exc_manager.add(BaseException, self.on_exception)

    def on_started(self, event):
        print("Scanner: started")

    def on_finished(self, event):
        print("Scanner: finished")

    def on_next_target(self, event, target):
        path = get_path_with_schema(target)
        print("Next %s target: [%s]" % (target.type, path))

    def on_worker_started(self, event, worker):
        worker.add_receiver(self.worker_receiver)

    def on_error(self, event, exception):
        self.exc_manager.handle(exception, event.emitter)

    def on_disk_error(self, exc, scanner):
        target = scanner.cur_target
        path = get_path_with_schema(target)

        print("[%s]: error: %s: %s" % (path, exc.error_type, exc))

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

        if target.status in ("finished", "failed", "suspended"):
            path = get_path_with_schema(target)
            print("[%s]: %s" % (path, target.status))

        if target.status == "finished":
            print_target_totals(self.env, target)

    def on_duplicates_found(self, event, duplicates):
        print("Found %d duplicates of %s" % (len(duplicates) - 1, duplicates[0].path))

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
        path = get_path_with_schema(target)

        print("[%s]: error: %s: %s" % (path, exc.error_type, exc))

    def on_exception(self, exc, scanner):
        traceback.print_exc()

def do_scan(env, names):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    common.cleanup_filelists(env)

    n_workers = env.get("n_workers", encsync.scan_threads)
    ask = env.get("ask", False)
    no_choice = env.get("no_choice", False)

    names = list(names)

    if env.get("all", False):
        for target in encsync.targets:
            if not env.get("remote_only", False):
                names.append(target["name"] + ":local")

            if not env.get("local_only", False):
                names.append(target["name"] + ":remote")

    if len(names) == 0:
        show_error("Error: no targets given")
        return 1

    no_journal = env.get("no_journal", False)

    scanner = Scanner(env["encsync"], env["db_dir"], n_workers, enable_journal=not no_journal)

    with GenericSignalManager(scanner):
        targets = []

        target_receiver = TargetReceiver(env)

        for name in names:
            if name.endswith(":local"):
                scan_type = "local"
                name = name[:-6]
            elif name.endswith(":remote"):
                scan_type = "remote"
                name = name[:-7]
            else:
                scan_type = None

            local_path = None
            remote_path = None

            for target in encsync.targets:
                if target["name"] == name:
                    if scan_type != "remote":
                        local_path = target["local"]
                        local_path = os.path.abspath(os.path.expanduser(local_path))

                    if scan_type != "local":
                        remote_path = target["remote"]
                        remote_path = common.prepare_remote_path(remote_path)

                    break

            if local_path is not None:
                targets.append(ScanTarget("local", name, local_path))
            if remote_path is not None:
                targets.append(ScanTarget("remote", name, remote_path))

            if local_path is None and remote_path is None:
                show_error("Error: unknown target %r" % (name,))
                return 1

        if ask and not no_choice:
            targets = ask_target_choice(targets)

        for target in targets:
            scanner.add_target(target)
            target.add_receiver(target_receiver)

        print("Targets to scan:")
        for target in targets:
            print("[%s]" % get_path_with_schema(target))

        scanner_receiver = ScannerReceiver(scanner)

        scanner.add_receiver(scanner_receiver)

        scanner.start()
        scanner.join()

        if any(i.status != "finished" for i in targets):
            return 1

        return 0
