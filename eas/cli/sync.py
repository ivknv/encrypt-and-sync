#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

import portalocker

from . import common
from .authenticate_storages import authenticate_storages
from .common import show_error, get_progress_str
from .scan import ScannerReceiver
from .remove_duplicates import DuplicateRemoverReceiver
from .pager import Pager

from ..synchronizer import Synchronizer, SyncTarget
from ..events import Receiver
from ..filelist import DuplicateList
from ..difflist import DiffList
from .generic_signal_manager import GenericSignalManager
from .parse_choice import interpret_choice
from ..common import Lockfile

__all__ = ["do_sync", "SynchronizerReceiver"]

def ask_target_choice(targets):
    for i, target in enumerate(targets):
        print("[%d] [%s -> %s]" % (i + 1,
                                   target.folder1["name"],
                                   target.folder2["name"]))

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
            show_error("Error: %s" % str(e))

def count_duplicates(env, folder_storage):
    duplist = DuplicateList(folder_storage.storage.name, env["db_dir"])
    duplist.create()

    return duplist.get_children_count(folder_storage.prefix)

def print_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    folder_name1 = target.folder1["name"]
    folder_name2 = target.folder2["name"]

    n_duplicates = 0

    if target.src.encrypted:
        n_duplicates += count_duplicates(env, target.src)

    if target.dst.encrypted:
        n_duplicates += count_duplicates(env, target.dst)

    if not target.no_remove:
        n_rm = difflist.count_rm_differences(folder_name1, folder_name2)
    else:
        n_rm = 0
    n_dirs = difflist.count_dirs_differences(folder_name1, folder_name2)
    n_new_files = difflist.count_new_file_differences(folder_name1, folder_name2)
    n_update = difflist.count_update_differences(folder_name1, folder_name2)

    print("[%s -> %s]: %d duplicate removals" % (folder_name1, folder_name2,
                                                 n_duplicates))

    if target.no_remove:
        print("[%s -> %s]: 0 removals (disabled)" % (folder_name1, folder_name2))
    else:
        print("[%s -> %s]: %d removals" % (folder_name1, folder_name2, n_rm))

    print("[%s -> %s]: %d new directories" % (folder_name1, folder_name2, n_dirs))
    print("[%s -> %s]: %d new files to upload" % (folder_name1, folder_name2,
                                                  n_new_files))
    print("[%s -> %s]: %d files to update" % (folder_name1, folder_name2, n_update))

def ask_continue():
    answer = None
    values = {"y": "continue", "n": "stop", "v": "view", "s": "skip"}

    default = "y"

    try:
        while answer not in values.keys():
            answer = input("Continue synchronization? [Y/n/(s)kip/(v)iew differences]: ").lower()

            if answer == "":
                answer = default
    except (KeyboardInterrupt, EOFError):
        answer = "n"

    return values[answer]

def view_diffs(env, target):
    funcs = {"r":  view_rm_diffs,       "d":  view_dirs_diffs,
             "f":  view_new_file_diffs, "u":  view_update_diffs,
             "du": view_duplicates}

    s = "What differences? [(r)m/(d)irs/new (f)iles/(u)pdates/(du)plicates/(s)top]: "

    while True:
        answer = input(s).lower()

        if answer in funcs.keys():
            funcs[answer](env, target)
        elif answer == "s":
            break

def view_rm_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("Removals:\n")

    diff_count = difflist.count_rm_differences(target.folder1["name"], target.folder2["name"])

    diffs = difflist.select_rm_differences(target.folder1["name"], target.folder2["name"])

    if diff_count < 50:
        pager.command = None

    for diff in diffs:
        pager.stdin.write("  %s %s\n" % (diff["node_type"], diff["path"]))

    pager.run()

def view_dirs_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("New directories:\n")

    diff_count = difflist.count_dirs_differences(target.folder1["name"], target.folder2["name"])

    diffs = difflist.select_dirs_differences(target.folder1["name"], target.folder2["name"])

    if diff_count < 50:
        pager.command = None

    for diff in diffs:
        pager.stdin.write("  %s\n" % (diff["path"],))

    pager.run()

def view_new_file_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("New files to upload:\n")

    diff_count = difflist.count_new_file_differences(target.folder1["name"], target.folder2["name"])

    if diff_count < 50:
        pager.command = None

    diffs = difflist.select_new_file_differences(target.folder1["name"], target.folder2["name"])

    for diff in diffs:
        pager.stdin.write("  %s\n" % (diff["path"],))

    pager.run()

def view_update_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("Files to update:\n")

    diff_count = difflist.count_update_differences(target.folder1["name"], target.folder2["name"])

    if diff_count < 50:
        pager.command = None

    diffs = difflist.select_update_differences(target.folder1["name"], target.folder2["name"])

    for diff in diffs:
        pager.stdin.write("  %s\n" % (diff["path"],))

    for diff in diffs:
        pager.stdin.write("  %s\n" % (diff["path"],))

    pager.run()

def view_duplicates(env, target):
    duplist1 = DuplicateList(target.src.storage.name, env["db_dir"])
    duplist1.create()

    duplist2 = DuplicateList(target.dst.storage.name, env["db_dir"])
    duplist2.create()

    pager = Pager()

    count = duplist1.get_children_count(target.src.prefix)
    count += duplist2.get_children_count(target.dst.prefix)

    if count < 50:
        pager.command = None

    if target.src.encrypted:
        duplicates = duplist1.find_children(target.src.prefix)

        for duplicate in duplicates:
            pager.stdin.write("  %s %s\n" % (duplicate[0], duplicate[2]))

    if target.dst.encrypted:
        duplicates = duplist2.find_children(target.dst.prefix)

        for duplicate in duplicates:
            pager.stdin.write("  %s %s\n" % (duplicate[0], duplicate[2]))

    pager.run()

def print_target_totals(target):
    n_finished = target.progress["finished"] + target.progress["skipped"]
    n_failed = target.progress["failed"]
    n_total = target.total_children

    print("[%s -> %s]: %d tasks in total" % (target.folder1["name"],
                                             target.folder2["name"], n_total))
    print("[%s -> %s]: %d tasks successful" % (target.folder1["name"],
                                               target.folder2["name"], n_finished))
    print("[%s -> %s]: %d tasks failed" % (target.folder1["name"],
                                           target.folder2["name"], n_failed))

class SynchronizerReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.env = env

    def on_next_target(self, event, target):
        target.add_receiver(TargetReceiver(self.env, target))
        print("Next target: [%s -> %s]" % (target.folder1["name"], target.folder2["name"]))

    def on_error(self, event, exc):
        common.show_exception(exc)

class PoolReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.worker_receiver = WorkerReceiver(env)

    def on_spawn(self, event, worker):
        worker.add_receiver(self.worker_receiver)

class TargetReceiver(Receiver):
    def __init__(self, env, target):
        Receiver.__init__(self)

        self.env = env

        self.pool_receiver = PoolReceiver(env)
        self.scanner_receiver = ScannerReceiver(env, target.scanner)
        self.duprem_receiver = DuplicateRemoverReceiver(env, target.duprem, False)

    def on_status_changed(self, event):
        target = event["emitter"]
        status = target.status

        if status != "pending":
            print("[%s -> %s]: %s" % (target.folder1["name"],
                                      target.folder2["name"], status))
        else:
            target.pool.add_receiver(self.pool_receiver)

        if status in ("finished", "failed"):
            print_target_totals(target)

    def on_integrity_check(self, event):
        target = event["emitter"]
        print("[%s -> %s]: integrity check" % (target.folder1["name"],
                                               target.folder2["name"]))

    def on_integrity_check_finished(self, event):
        target = event["emitter"]
        print("[%s -> %s]: integrity check: finished" % (target.folder1["name"],
                                                         target.folder2["name"]))

    def on_integrity_check_failed(self, event):
        target = event["emitter"]
        print("[%s -> %s]: integrity check: failed" % (target.folder1["name"],
                                                       target.folder2["name"]))

    def on_diffs_started(self, event):
        target = event.emitter

        print("[%s -> %s]: building the difference table" % (target.folder1["name"],
                                                             target.folder2["name"]))

    def on_diffs_failed(self, event):
        target = event.emitter

        print("[%s -> %s]: failed to build the difference table" % (target.folder1["name"],
                                                                    target.folder2["name"]))

    def on_diffs_finished(self, event):
        target = event.emitter

        print("[%s -> %s]: finished building the difference table" % (target.folder1["name"],
                                                                      target.folder2["name"]))

    def on_entered_stage(self, event, stage):
        if self.env.get("no_progress", False):
            return

        target = event.emitter

        if stage == "scan" and not target.enable_scan:
            return

        if stage == "check" and target.skip_integrity_check:
            return

        if stage in ("scan", "check"):
            target.scanner.add_receiver(self.scanner_receiver)
        elif stage == "rmdup":
            target.duprem.add_receiver(self.duprem_receiver)

        print("[%s -> %s]: entered stage %r" % (target.folder1["name"],
                                                target.folder2["name"], stage))

    def on_exited_stage(self, event, stage):
        target = event.emitter

        if self.env.get("no_progress", False):
            if stage == "scan":
                print_diffs(self.env, target)

            return

        if stage == "scan":
            if target.status == "pending":
                print_diffs(self.env, target)

                ask = self.env.get("ask", False)
                no_diffs = self.env.get("no_diffs", False)

                if not target.total_children:
                    print("[%s -> %s]: nothing to do" % (target.folder1["name"],
                                                         target.folder2["name"]))
                    target.status = "finished"
                    return

                if ask and not no_diffs:
                    action = ask_continue()

                    while action == "view":
                        view_diffs(self.env, target)
                        action = ask_continue()

                    if action == "stop":
                        target.synchronizer.stop()
                    elif action == "skip":
                        target.status = "skipped"

                if not target.enable_scan:
                    return
        elif stage == "check" and target.skip_integrity_check:
            return

        print("[%s -> %s]: exited stage %r" % (target.folder1["name"],
                                               target.folder2["name"], stage))

class WorkerReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.env = env
        self.task_receiver = TaskReceiver()

    def on_next_task(self, event, task):
        if self.env.get("no_progress", False):
            return

        msg = get_progress_str(task) + ": "

        if task.type == "new":
            if task.node_type == "f":
                msg += "uploading file"
            elif task.node_type == "d":
                msg += "creating directory"
        elif task.type == "update":
            msg += "updating file"
        elif task.type == "rm":
            if task.node_type == "f":
                msg += "removing file"
            elif task.node_type == "d":
                msg += "removing directory"
        elif task.type == "rmdup":
            if task.node_type == "f":
                msg += "removing file duplicate"
            elif task.node_type == "f":
                msg += "removing directory duplicate"

        print(msg)

        task.add_receiver(self.task_receiver)

    def on_error(self, event, exc):
        common.show_exception(exc)

class TaskReceiver(Receiver):
    def __init__(self):
        Receiver.__init__(self)

        self.last_uploaded_percents = {}
        self.last_downloaded_percents = {}

    def on_status_changed(self, event):
        task = event["emitter"]

        status = task.status

        if status in (None, "pending"):
            return

        progress_str = get_progress_str(task)

        print(progress_str + ": %s" % status)

        self.last_uploaded_percents.pop(task.path, None)
        self.last_downloaded_percents.pop(task.path, None)

    def on_downloaded_changed(self, event):
        task = event["emitter"]
        downloaded, size = task.downloaded, task.download_controller.size

        try:
            downloaded_percent = float(downloaded) / size * 100.0
        except ZeroDivisionError:
            downloaded_percent = 100.0

        last_downloaded = self.last_downloaded_percents.get(task.path, 0.0)

        # Change can be negative due to retries
        if abs(downloaded_percent - last_downloaded) < 25.0 and downloaded_percent < 100.0:
            return

        self.last_downloaded_percents[task.path] = downloaded_percent

        progress_str = get_progress_str(task)

        print(progress_str + ": received %6.2f%%" % downloaded_percent)

    def on_uploaded_changed(self, event):
        task = event["emitter"]
        uploaded, size = task.uploaded, task.size

        try:
            uploaded_percent = float(uploaded) / size * 100.0
        except ZeroDivisionError:
            uploaded_percent = 100.0

        last_uploaded = self.last_uploaded_percents.get(task.path, 0.0)

        # Change can be negative due to retries
        if abs(uploaded_percent - last_uploaded) < 25.0 and uploaded_percent < 100.0:
            return

        self.last_uploaded_percents[task.path] = uploaded_percent

        progress_str = get_progress_str(task)

        print(progress_str + ": sent %6.2f%%" % uploaded_percent)

def do_sync(env, names):
    lockfile = Lockfile(env["lockfile_path"])

    try:
        lockfile.acquire()
    except portalocker.exceptions.AlreadyLocked:
        common.show_error("Error: there can be only one Encrypt & Sync (the lockfile is already locked)")
        return 1

    config, ret = common.make_config(env)

    if config is None:
        return ret

    no_scan = env.get("no_scan", False)
    no_check = env.get("no_check", False)
    no_remove = env.get("no_remove", False)
    choose_targets = env.get("choose_targets", False)
    ask = env.get("ask", False)

    names = list(names)

    if env.get("all", False):
        for folder1, folder2 in config.sync_targets:
            names.append(folder1)
            names.append(folder2)

    if len(names) == 0:
        show_error("Error: no folders given")
        return 1

    if len(names) % 2 != 0:
        show_error("Error: invalid number of arguments")
        return 1

    n_sync_workers = env.get("n_workers", config.sync_threads)
    n_scan_workers = env.get("n_workers", config.scan_threads)
    no_journal = env.get("no_journal", False)
    no_preserve_modified = env.get("no_preserve_modified", False)

    synchronizer = Synchronizer(config,
                                env["db_dir"],
                                enable_journal=not no_journal)

    synchronizer.upload_limit = config.upload_limit
    synchronizer.download_limit = config.download_limit

    synchronizer_receiver = SynchronizerReceiver(env)
    synchronizer.add_receiver(synchronizer_receiver)

    targets = []

    for name1, name2 in zip(names[::2], names[1::2]):
        target = SyncTarget(synchronizer, name1, name2, not no_scan)
        target.skip_integrity_check = no_check
        target.no_remove = no_remove
        target.n_workers = n_sync_workers
        target.n_scan_workers = n_scan_workers
        target.preserve_modified = not no_preserve_modified

        targets.append(target)

    if (ask and env.get("all", False)) or choose_targets:
        targets = ask_target_choice(targets)

    for target in targets:
        synchronizer.add_target(target)

    print("Targets to sync:")
    for target in targets:
        print("[%s -> %s]" % (target.folder1["name"], target.folder2["name"]))

    storage_names = {i.folder1["type"] for i in targets}
    storage_names |= {i.folder2["type"] for i in targets}

    ret = authenticate_storages(env, storage_names)

    if ret:
        return ret

    with GenericSignalManager(synchronizer):
        print("Synchronizer: starting")

        # This contraption is needed to silence a SystemExit traceback
        # The traceback would be printed otherwise due to use of a finally clause
        try:
            try:
                synchronizer.run()
            finally:
                print("Synchronizer: finished")
        except SystemExit as e:
            sys.exit(e.code)

    if any(i.status not in ("finished", "skipped") for i in targets):
        return 1

    if synchronizer.stopped:
        return 1

    return 0
