# -*- coding: utf-8 -*-

import os
import sys

import portalocker

from ..duplicate_remover import DuplicateRemover, DuplicateRemoverTarget
from ..duplicate_list import DuplicateList
from ..events import Receiver
from .. import pathm
from ..common import Lockfile

from .authenticate_storages import authenticate_storages

from . import common
from .generic_signal_manager import GenericSignalManager
from .parse_choice import interpret_choice
from .pager import Pager

__all__ = ["remove_duplicates", "DuplicateRemoverReceiver"]

def ask_target_choice(targets):
    for i, target in enumerate(targets):
        print("[%d] [%s://%s]" % (i + 1, target.storage_name, target.path))

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
            common.show_error("Error: %s" % str(e))

def ask_continue(duprem):
    answer = None
    values = {"y": "continue", "n": "stop", "v": "view", "s": "skip"}

    default = "y"

    try:
        while answer not in values.keys():
            if duprem.stopped:
                return "stop"

            answer = input("Continue duplicate removal? [Y/n/(s)kip/(v)iew duplicates]: ").lower()

            if answer == "":
                answer = default
    except (KeyboardInterrupt, EOFError):
        answer = "n"

    return values[answer]

def count_duplicates(env, target):
    duplist = DuplicateList(target.storage_name, env["db_dir"])
    duplist.create()

    return duplist.get_file_count(target.path)

def view_duplicates(env, target):
    duplist = DuplicateList(target.storage_name, env["db_dir"])
    duplist.create()

    duplicate_count = duplist.get_file_count(target.path)
    duplicates = duplist.find_recursively(target.path)

    pager = Pager()
    pager.stdin.write("Duplicates:\n")

    if duplicate_count < 50:
        pager.command = None

    for duplicate in duplicates:
        pager.stdin.write("  %s %s\n" % (duplicate[0], duplicate[2]))

    pager.run()

def print_target_totals(target):
    n_finished = target.progress["finished"] + target.progress["skipped"]
    n_failed = target.progress["failed"]
    n_total = target.total_children

    print("[%s://%s]: %d tasks in total" % (target.storage_name,
                                            target.path, n_total))
    print("[%s://%s]: %d tasks successful" % (target.storage_name,
                                              target.path, n_finished))
    print("[%s://%s]: %d tasks failed" % (target.storage_name,
                                           target.path, n_failed))

class DuplicateRemoverReceiver(Receiver):
    def __init__(self, env, duprem, interactive_continue=True):
        Receiver.__init__(self)

        self.duprem = duprem
        self.env = env
        self.interactive_continue = interactive_continue

        self.target_receiver = TargetReceiver(env)

    def on_next_target(self, event, target):
        target.add_receiver(self.target_receiver)
        
        print("Removing duplicates: [%s://%s]" % (target.storage_name, target.path,))

        n_duplicates = count_duplicates(self.env, target)

        print("[%s://%s]: %d duplicates to remove" % (target.storage_name,
                                                      target.path, n_duplicates,))

        if not self.interactive_continue or not self.env.get("ask", False):
            return

        action = ask_continue(self.duprem)

        while action == "view":
            view_duplicates(self.env, target)
            action = ask_continue(self.duprem)

        if action == "stop":
            self.duprem.stop()
        elif action == "skip":
            target.change_status("skipped")

    def on_error(self, event, exc):
        common.show_exception(exc)

class PoolReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.worker_receiver = WorkerReceiver(env)

    def on_spawn(self, event, worker):
        worker.add_receiver(self.worker_receiver)

class TargetReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.pool_receiver = PoolReceiver(env)

    def on_status_changed(self, event):
        target = event["emitter"]
        status = target.status

        if status != "pending":
            print("[%s://%s]: %s" % (target.storage_name, target.path, status))
        else:
            target.pool.add_receiver(self.pool_receiver)

        if status in ("finished", "failed"):
            print_target_totals(target)

class WorkerReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.env = env
        self.task_receiver = TaskReceiver()

    def on_next_task(self, event, task):
        if self.env.get("no_progress", False):
            return

        print(common.get_progress_str(task) + ": " + "removing duplicate")
        task.add_receiver(self.task_receiver)

    def on_error(self, event, exc):
        common.show_exception(exc)

class TaskReceiver(Receiver):
    def on_status_changed(self, event):
        task = event["emitter"]

        status = task.status

        if status in (None, "pending"):
            return

        progress_str = common.get_progress_str(task)

        print(progress_str + ": %s" % status)

def remove_duplicates(env, paths):
    lockfile = Lockfile(env["lockfile_path"])

    try:
        lockfile.acquire()
    except portalocker.exceptions.AlreadyLocked:
        common.show_error("Error: there can be only one Encrypt & Sync (the lockfile is already locked)")
        return 1

    config, ret = common.make_config(env)

    if config is None:
        return ret

    # pathm were supplied by user
    user_paths = True

    choose_targets = env.get("choose_targets", False)
    ask = env.get("ask", False)

    if env.get("all", False):
        choose_targets = choose_targets or ask
        paths = []

        # pathm are from the configuration
        user_paths = False

        for folder in config.folders.values():
            folder_path = folder["type"] + "://" + folder["path"]
            paths.append(folder_path)

    n_workers = env.get("n_workers", config.sync_threads)
    no_journal = env.get("no_journal", False)
    no_preserve_modified = env.get("no_preserve_modified", False)

    duprem = DuplicateRemover(config, env["db_dir"], enable_journal=not no_journal)
    targets = []

    for path in paths:
        path, path_type = common.recognize_path(path)

        if path_type == "local":
            path = pathm.from_sys(os.path.abspath(pathm.to_sys(path)))
        else:
            path = pathm.join_properly("/", path)

        try:
            target = DuplicateRemoverTarget(duprem, path_type, path)
            target.n_workers = n_workers
            target.preserve_modified = not no_preserve_modified
            targets.append(target)
        except ValueError as e:
            if user_paths:
                common.show_error("Error: " + str(e))

    if choose_targets:
        targets = ask_target_choice(targets)

    for target in targets:
        duprem.add_target(target)

    print("Duplicate remover targets:")
    for target in targets:
        print("[%s://%s]" % (target.storage_name, target.path))

    duprem.add_receiver(DuplicateRemoverReceiver(env, duprem))

    ret = authenticate_storages(env, {i.storage_name for i in targets})

    if ret:
        return ret

    with GenericSignalManager(duprem):
        print("Duplicate remover: starting")

        # This contraption is needed to silence a SystemExit traceback
        # The traceback would be printed otherwise due to use of a finally clause
        try:
            try:
                duprem.run()
            finally:
                print("Duplicate remover: finished")
        except SystemExit as e:
            sys.exit(e.code)

    if any(i.status not in ("finished", "skipped") for i in targets):
        return 1

    if duprem.stopped:
        return 1

    return 0
