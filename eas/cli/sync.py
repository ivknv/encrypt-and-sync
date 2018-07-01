#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools

try:
    import grp
    import pwd
except ImportError:
    grp = pwd = None

import os
import sys
import time

import portalocker

from . import common
from .authenticate_storages import authenticate_storages
from .common import show_error, get_progress_str
from .scan import ScannerReceiver
from .remove_duplicates import DuplicateRemoverReceiver
from .pager import Pager

from ..synchronizer import Synchronizer, SyncTarget
from ..events import Receiver
from ..duplicate_list import DuplicateList
from ..difflist import DiffList
from .generic_signal_manager import GenericSignalManager
from .parse_choice import interpret_choice
from ..common import Lockfile, validate_folder_name, recognize_path
from .. import pathm

__all__ = ["do_sync", "SynchronizerReceiver"]

def get_target_display_name(target):
    if pathm.is_equal(target.path1, target.folder1["path"]):
        name1 = target.folder1["name"]
    else:
        path = pathm.cut_prefix(target.path1, target.folder1["path"])
        path = path.lstrip("/") or "/"

        name1 = "[%s][%s]" % (target.folder1["name"], path)

    if pathm.is_equal(target.path2, target.folder2["path"]):
        name2 = target.folder2["name"]
    else:
        path = pathm.cut_prefix(target.path2, target.folder2["path"])
        path = path.lstrip("/") or "/"

        name2 = "[%s][%s]" % (target.folder2["name"], path)

    return "[%s -> %s]" % (name1, name2)

def ask_target_choice(targets):
    for i, target in enumerate(targets):
        display_name = get_target_display_name(target)
        print("[%d] %s" % (i + 1, display_name))

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

    return duplist.get_file_count(folder_storage.prefix)

def print_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    n_duplicates = 0

    if target.src.encrypted:
        n_duplicates += count_duplicates(env, target.src)

    if target.dst.encrypted:
        n_duplicates += count_duplicates(env, target.dst)

    if not target.no_remove:
        n_rm = difflist.count_rm(target.path1_with_proto,
                                 target.path2_with_proto)
    else:
        n_rm = 0

    n_dirs = difflist.count_dirs(target.path1_with_proto,
                                 target.path2_with_proto)
    n_new_files = difflist.count_new_file(target.path1_with_proto,
                                          target.path2_with_proto)
    n_update = difflist.count_update(target.path1_with_proto,
                                     target.path2_with_proto)
    n_modified = difflist.count_modified(target.path1_with_proto,
                                         target.path2_with_proto)
    n_chmod = difflist.count_chmod(target.path1_with_proto,
                                   target.path2_with_proto)
    n_chown = difflist.count_chown(target.path1_with_proto,
                                   target.path2_with_proto)

    display_name = get_target_display_name(target)

    print("%s: %d duplicate removals" % (display_name, n_duplicates))

    if target.no_remove:
        print("%s: 0 removals (disabled)" % (display_name,))
    else:
        print("%s: %d removals" % (display_name, n_rm))

    print("%s: %d new directories" % (display_name, n_dirs))
    print("%s: %d new files to upload" % (display_name, n_new_files))
    print("%s: %d files to update" % (display_name, n_update))

    if target.sync_modified:
        print("%s: %d files to set modified date for" % (display_name, n_modified))
    else:
        print("%s: 0 files to set modified date for (disabled)" % (display_name,))

    if target.sync_mode:
        print("%s: %d files to set mode for" % (display_name, n_chmod))
    else:
        print("%s: 0 files to set mode for (disabled)" % (display_name,))

    if target.sync_ownership:
        print("%s: %d files to set ownership for" % (display_name, n_chown))
    else:
        print("%s: 0 files to set ownership for (disabled)" % (display_name,))

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
             "du": view_duplicates,     "m":  view_modified_diffs,
             "c":  view_chmod_diffs,    "o":  view_chown_diffs}

    s = "What differences?\n[(r)m / (d)irs /new (f)iles / (u)pdates / (m)odified / (c)hmod / ch(o)wn / (du)plicates / (s)top]: "

    while True:
        answer = input(s).lower()

        if answer in funcs.keys():
            funcs[answer](env, target)
        elif answer == "s":
            break

@functools.lru_cache(maxsize=1024)
def _get_diff_dst_subpath(config, dst_path):
    dst_path, dst_path_type = recognize_path(dst_path)

    dst_folder = config.identify_folder(dst_path_type, dst_path)

    if dst_folder is None:
        dst_subpath = "/"
    else:
        dst_subpath = pathm.cut_prefix(dst_path, dst_folder["path"])
        dst_subpath = pathm.join("/", dst_subpath)

    return dst_subpath

def get_diff_dst_subpath(config, diff):
    return _get_diff_dst_subpath(config, diff["dst_path"])

def get_diff_dst_path(config, diff):
    dst_path = recognize_path(diff["dst_path"])[0]
    dst_subpath = get_diff_dst_subpath(config, diff)

    dst_path = pathm.join(dst_subpath, diff["path"])
    dst_path = dst_path.lstrip("/") or "/"

    return dst_path

def format_diff(config, diff):
    assert(diff["type"] in ("new", "update", "rm", "modified", "chmod", "chown"))

    if diff["type"] in ("new", "update"):
        return format_new_diff(config, diff)
    elif diff["type"] == "rm":
        return format_rm_diff(config, diff)
    elif diff["type"] == "modified":
        return format_modified_diff(config, diff)
    elif diff["type"] == "chmod":
        return format_chmod_diff(config, diff)
    elif diff["type"] == "chown":
        return format_chown_diff(config, diff)

    assert(False)

def format_new_diff(config, diff):
    dst_path = get_diff_dst_path(config, diff)

    return "%s\n" % (dst_path,)

def format_rm_diff(config, diff):
    dst_path = get_diff_dst_path(config, diff)

    return "%s %s\n" % (diff["node_type"], dst_path,)

def format_modified_diff(config, diff):
    dst_path = get_diff_dst_path(config, diff)

    return "%s %s %r\n" % (diff["node_type"], dst_path, time.ctime(diff["modified"]))

def format_chmod_diff(config, diff):
    dst_path = get_diff_dst_path(config, diff)

    return "%s %s %s\n" % (diff["node_type"], dst_path, oct(diff["mode"])[2:])

def format_chown_diff(config, diff):
    dst_path = get_diff_dst_path(config, diff)

    ownership_string = ""

    if pwd is None or grp is None:
        if diff["owner"] is not None:
            ownership_string = str(diff["owner"])

        if diff["group"] is not None:
            ownership_string = ":%s" % (diff["group"],)
    else:
        if diff["owner"] is not None:
            try:
                ownership_string += pwd.getpwuid(diff["owner"]).pw_name
            except KeyError:
                ownership_string += str(diff["owner"])

        if diff["group"] is not None:
            try:
                ownership_string += ":" + grp.getgrgid(diff["group"]).gr_name
            except KeyError:
                ownership_string += ":%s" % (diff["group"],)

    return "%s %s %s\n" % (diff["node_type"], dst_path, ownership_string)

def view_rm_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("Removals:\n")

    diff_count = difflist.count_rm(target.path1_with_proto, target.path2_with_proto)

    diffs = difflist.find_rm(target.path1_with_proto, target.path2_with_proto)

    if diff_count < 50:
        pager.command = None

    for diff in diffs:
        pager.stdin.write("  " + format_diff(env["config"], diff))

    pager.run()

def view_dirs_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("New directories:\n")

    diff_count = difflist.count_dirs(target.path1_with_proto, target.path2_with_proto)

    diffs = difflist.find_dirs(target.path1_with_proto, target.path2_with_proto)

    if diff_count < 50:
        pager.command = None

    for diff in diffs:
        pager.stdin.write("  " + format_diff(env["config"], diff))

    pager.run()

def view_new_file_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("New files to upload:\n")

    diff_count = difflist.count_new_file(target.path1_with_proto, target.path2_with_proto)

    if diff_count < 50:
        pager.command = None

    diffs = difflist.find_new_file(target.path1_with_proto, target.path2_with_proto)

    for diff in diffs:
        pager.stdin.write("  " + format_diff(env["config"], diff))

    pager.run()

def view_update_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("Files to update:\n")

    diff_count = difflist.count_update(target.path1_with_proto, target.path2_with_proto)

    if diff_count < 50:
        pager.command = None

    diffs = difflist.find_update(target.path1_with_proto, target.path2_with_proto)

    for diff in diffs:
        pager.stdin.write("  " + format_diff(env["config"], diff))

    pager.run()

def view_modified_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("Files to set modified date for:\n")

    diff_count = difflist.count_modified(target.path1_with_proto, target.path2_with_proto)

    if diff_count < 50:
        pager.command = None

    diffs = difflist.find_modified(target.path1_with_proto, target.path2_with_proto)

    for diff in diffs:
        pager.stdin.write("  " + format_diff(env["config"], diff))

    pager.run()

def view_chmod_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("Files to set mode for:\n")

    diff_count = difflist.count_chmod(target.path1_with_proto, target.path2_with_proto)

    if diff_count < 50:
        pager.command = None

    diffs = difflist.find_chmod(target.path1_with_proto, target.path2_with_proto)

    for diff in diffs:
        pager.stdin.write("  " + format_diff(env["config"], diff))

    pager.run()

def view_chown_diffs(env, target):
    difflist = DiffList(env["db_dir"])

    pager = Pager()
    pager.stdin.write("Files to set ownership for:\n")

    diff_count = difflist.count_chown(target.path1_with_proto, target.path2_with_proto)

    if diff_count < 50:
        pager.command = None

    diffs = difflist.find_chown(target.path1_with_proto, target.path2_with_proto)

    for diff in diffs:
        pager.stdin.write("  " + format_diff(env["config"], diff))

    pager.run()

def view_duplicates(env, target):
    duplist1 = DuplicateList(target.src.storage.name, env["db_dir"])
    duplist1.create()

    duplist2 = DuplicateList(target.dst.storage.name, env["db_dir"])
    duplist2.create()

    pager = Pager()

    count = duplist1.get_file_count(target.src.prefix)
    count += duplist2.get_file_count(target.dst.prefix)

    if count < 50:
        pager.command = None

    pager.stdin.write("Duplicates to remove:\n")

    if target.src.encrypted:
        duplicates = duplist1.find_recursively(target.src.prefix)

        for duplicate in duplicates:
            pager.stdin.write("  %s %s\n" % (duplicate[0], duplicate[2]))

    if target.dst.encrypted:
        duplicates = duplist2.find_recursively(target.dst.prefix)

        for duplicate in duplicates:
            pager.stdin.write("  %s %s\n" % (duplicate[0], duplicate[2]))

    pager.run()

def print_target_totals(target):
    n_finished = target.progress["finished"] + target.progress["skipped"]
    n_failed = target.progress["failed"]
    n_total = target.total_children

    display_name = get_target_display_name(target)

    print("%s: %d tasks in total" % (display_name, n_total))
    print("%s: %d tasks successful" % (display_name, n_finished))
    print("%s: %d tasks failed" % (display_name, n_failed))

class SynchronizerReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.env = env

    def on_next_target(self, event, target):
        target.add_receiver(TargetReceiver(self.env, target))
        display_name = get_target_display_name(target)

        print("Next target: %s" % (display_name))

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

        display_name = get_target_display_name(target)

        if status != "pending":
            print("%s: %s" % (display_name, status))
        else:
            target.pool.add_receiver(self.pool_receiver)

        if status in ("finished", "failed"):
            print_target_totals(target)

    def on_integrity_check(self, event):
        target = event["emitter"]
        display_name = get_target_display_name(target)

        print("%s: integrity check" % (display_name,))

    def on_integrity_check_finished(self, event):
        target = event["emitter"]
        display_name = get_target_display_name(target)

        print("%s: integrity check: finished" % (display_name,))

    def on_integrity_check_failed(self, event):
        target = event["emitter"]
        display_name = get_target_display_name(target)

        print("%s: integrity check: failed" % (display_name,))

    def on_diffs_started(self, event):
        target = event.emitter
        display_name = get_target_display_name(target)

        print("%s: building the difference table" % (display_name,))

    def on_diffs_failed(self, event):
        target = event.emitter
        display_name = get_target_display_name(target)

        print("%s: failed to build the difference table" % (display_name,))

    def on_diffs_finished(self, event):
        target = event.emitter
        display_name = get_target_display_name(target)

        print("%s: finished building the difference table" % (display_name,))

        if target.stage is not None and target.stage["name"] == "metadata":
            difflist = DiffList(self.env["db_dir"])
            n = difflist.count_metadata(target.path1_with_proto, target.path2_with_proto)

            if n:
                print("%s: %d metadata setting tasks" % (display_name, n))

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

        display_name = get_target_display_name(target)

        print("%s: entered stage %r" % (display_name, stage))

    def on_exited_stage(self, event, stage):
        target = event.emitter

        if self.env.get("no_progress", False):
            if stage == "scan":
                print_diffs(self.env, target)

            return

        display_name = get_target_display_name(target)

        if stage == "scan":
            if target.status == "pending":
                print_diffs(self.env, target)

                ask = self.env.get("ask", False)
                no_diffs = self.env.get("no_diffs", False)

                if not target.total_children:
                    print("%s: nothing to do" % (display_name,))
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
                        target.stop()

                if not target.enable_scan:
                    return
        elif stage == "check" and target.skip_integrity_check:
            return

        print("%s: exited stage %r" % (display_name, stage))

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
        elif task.type == "modified":
            msg += "setting modified date"
        elif task.type == "chmod":
            msg += "setting file mode"
        elif task.type == "chown":
            msg += "setting file ownership"

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
        downloaded, size = task.downloaded, task.download_task.size

        try:
            downloaded_percent = float(downloaded) / size * 100.0
        except ZeroDivisionError:
            downloaded_percent = 100.0

        last_downloaded = self.last_downloaded_percents.get(task.path, 0.0)

        percent_step_count = max(min(int(size / 1024.0**2), 100), 1)
        percent_step = 100.0 / percent_step_count

        # Change can be negative due to retries
        if abs(downloaded_percent - last_downloaded) < percent_step and downloaded_percent < 100.0:
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

        percent_step_count = max(min(int(size / 1024.0**2), 100), 1)
        percent_step = 100.0 / percent_step_count

        # Change can be negative due to retries
        if abs(uploaded_percent - last_uploaded) < percent_step and uploaded_percent < 100.0:
            return

        self.last_uploaded_percents[task.path] = uploaded_percent

        progress_str = get_progress_str(task)

        print(progress_str + ": sent %6.2f%%" % uploaded_percent)

def do_sync(env, names_or_paths):
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

    names_or_paths = list(names_or_paths)

    if env.get("all", False):
        for folder1, folder2 in config.sync_targets:
            names_or_paths.append(folder1)
            names_or_paths.append(folder2)

    if len(names_or_paths) == 0:
        show_error("Error: no folders or paths given")
        return 1

    if len(names_or_paths) % 2 != 0:
        show_error("Error: invalid number of arguments")
        return 1

    n_sync_workers = env.get("n_workers", config.sync_threads)
    n_scan_workers = env.get("n_workers", config.scan_threads)
    no_journal = env.get("no_journal", False)
    no_sync_modified = env.get("no_sync_modified", False)
    no_sync_mode = env.get("no_sync_mode", False)
    sync_ownership = env.get("sync_ownership", False)
    force_scan = env.get("force_scan", False)
    no_scan = no_scan and not force_scan

    synchronizer = Synchronizer(config,
                                env["db_dir"],
                                enable_journal=not no_journal)

    synchronizer.upload_limit = config.upload_limit
    synchronizer.download_limit = config.download_limit

    synchronizer_receiver = SynchronizerReceiver(env)
    synchronizer.add_receiver(synchronizer_receiver)

    targets = []

    for name_or_path1, name_or_path2 in zip(names_or_paths[::2], names_or_paths[1::2]):
        if validate_folder_name(name_or_path1):
            try:
                folder1 = config.folders[name_or_path1]
            except KeyError:
                show_error("Error: unknown folder %r" % (name_or_path1,))
                return 1

            path1_with_proto = folder1["type"] + "://" + folder1["path"]
        else:
            path1_with_proto = name_or_path1

            path, proto = recognize_path(path1_with_proto)

            if proto == "local":
                path = pathm.from_sys(os.path.abspath(os.path.expanduser(path)))

            path1_with_proto = proto + "://" + path

        if validate_folder_name(name_or_path2):
            try:
                folder2 = config.folders[name_or_path2]
            except KeyError:
                show_error("Error: unknown folder %r" % (name_or_path2,))
                return 1

            path2_with_proto = folder2["type"] + "://" + folder2["path"]
        else:
            path2_with_proto = name_or_path2

            path, proto = recognize_path(path2_with_proto)

            if proto == "local":
                path = pathm.from_sys(os.path.abspath(os.path.expanduser(path)))

            path2_with_proto = proto + "://" + path

        try:
            target = SyncTarget(synchronizer, path1_with_proto, path2_with_proto, not no_scan)
        except KeyError as e:
            show_error("Error: %s" % (e,))
            return 1

        target.skip_integrity_check = no_check
        target.no_remove = no_remove
        target.n_workers = n_sync_workers
        target.n_scan_workers = n_scan_workers
        target.sync_modified = not no_sync_modified
        target.sync_mode = not no_sync_mode
        target.sync_ownership = sync_ownership
        target.force_scan = force_scan

        targets.append(target)

    if (ask and env.get("all", False)) or choose_targets:
        targets = ask_target_choice(targets)

    for target in targets:
        synchronizer.add_target(target)

    print("Targets to sync:")
    for target in targets:
        display_name = get_target_display_name(target)

        print("%s" % (display_name,))

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
