#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import traceback

from yadisk.exceptions import YaDiskError

from . import common
from .common import show_error, get_progress_str
from .scan import WorkerReceiver as ScanWorkerReceiver
from .scan import TargetReceiver as ScanTargetReceiver

from .. import Paths
from ..Synchronizer import Synchronizer, SyncTarget
from ..Scanner.Workers import ScanWorker
from ..Event.EventHandler import EventHandler
from ..DiffList import DiffList
from .SignalManagers import GenericSignalManager
from .parse_choice import interpret_choice
from ..ExceptionManager import ExceptionManager
from ..Synchronizer.Exceptions import TooLongFilenameError

def ask_target_choice(targets):
    for i, target in enumerate(targets):
        local, remote = target.local, target.remote
        print("[%d] [%s -> %s]" % (i + 1, local, remote))

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

def print_diffs(env, encsync, target):
    difflist = DiffList(encsync, env["db_dir"])

    local, remote = target.local, target.remote

    n_rmdup = difflist.count_rmdup_differences(remote)
    n_rm = difflist.count_rm_differences(local, remote)
    n_dirs = difflist.count_dirs_differences(local, remote)
    n_new_files = difflist.count_new_file_differences(local, remote)
    n_update = difflist.count_update_differences(local, remote)

    print("[%s -> %s]: %d duplicate removals" % (local, remote, n_rmdup))
    print("[%s -> %s]: %d removals" % (local, remote, n_rm))
    print("[%s -> %s]: %d new directories" % (local, remote, n_dirs))
    print("[%s -> %s]: %d new files to upload" % (local, remote, n_new_files))
    print("[%s -> %s]: %d files to update" % (local, remote, n_update))

def ask_continue(synchronizer):
    answer = None
    values = {"y": "continue", "n": "stop", "v": "view", "s": "skip"}

    default = "y"

    try:
        while answer not in values.keys():
            if synchronizer.stopped:
                return "stop"

            answer = input("Continue synchronization? [Y/n/(s)kip/(v)iew differences]: ").lower()

            if answer == "":
                answer = default
    except (KeyboardInterrupt, EOFError):
        answer = "n"

    return values[answer]

def view_diffs(env, encsync, target):
    funcs = {"du": view_rmdup_diffs, "r": view_rm_diffs,
             "d":  view_dirs_diffs,  "f": view_new_file_diffs,
             "u":  view_update_diffs}

    s = "What differences? [(du)plicates/(r)m/(d)irs/new (f)iles/(u)pdates/(s)top]: "

    while True:
        answer = input(s).lower()

        if answer in funcs.keys():
            funcs[answer](env, encsync, target)
        elif answer == "s":
            break

def view_rmdup_diffs(env, encsync, target):
    local, remote = target.local, target.remote

    difflist = DiffList(encsync, env["db_dir"])

    diffs = difflist.select_rmdup_differences(remote)

    print("Duplicate removals:")
    for diff in diffs:
        print("  %s %s" % (diff[1], diff[2].remote))

def view_rm_diffs(env, encsync, target):
    local, remote = target.local, target.remote

    difflist = DiffList(encsync, env["db_dir"])

    diffs = difflist.select_rm_differences(local, remote)

    print("Removals:")
    for diff in diffs:
        print("  %s %s" % (diff[1], diff[2].remote))

def view_dirs_diffs(env, encsync, target):
    local, remote = target.local, target.remote

    difflist = DiffList(encsync, env["db_dir"])

    diffs = difflist.select_dirs_differences(local, remote)

    print("New directories:")
    for diff in diffs:
        print("  %s" % (diff[2].remote))

def view_new_file_diffs(env, encsync, target):
    local, remote = target.local, target.remote

    difflist = DiffList(encsync, env["db_dir"])

    diffs = difflist.select_new_file_differences(local, remote)

    print("New files to upload:")
    for diff in diffs:
        print("  %s" % (diff[2].local))

def view_update_diffs(env, encsync, target):
    local, remote = target.local, target.remote

    difflist = DiffList(encsync, env["db_dir"])

    diffs = difflist.select_update_differences(local, remote)

    print("Files to update:")
    for diff in diffs:
        print("  %s" % (diff[2].remote))

def print_target_totals(target):
    n_finished = target.progress["finished"]
    n_failed = target.progress["failed"]
    n_total = target.total_children

    print("[%s -> %s]: %d tasks in total" % (target.local, target.remote, n_total))
    print("[%s -> %s]: %d tasks successful" % (target.local, target.remote, n_finished))
    print("[%s -> %s]: %d tasks failed" % (target.local, target.remote, n_failed))

class SynchronizerReceiver(EventHandler):
    def __init__(self, env, synchronizer):
        EventHandler.__init__(self)

        self.worker_receiver = WorkerReceiver()
        self.scan_worker_receiver = ScanWorkerReceiver()
        self.env = env

        self.exc_manager = ExceptionManager()

        self.add_emitter_callback(synchronizer, "started", self.on_started)
        self.add_emitter_callback(synchronizer, "finished", self.on_finished)
        self.add_emitter_callback(synchronizer, "next_target", self.on_next_target)
        self.add_emitter_callback(synchronizer, "worker_started", self.on_worker_started)
        self.add_emitter_callback(synchronizer, "entered_stage", self.on_entered_stage)
        self.add_emitter_callback(synchronizer, "exited_stage", self.on_exited_stage)
        self.add_emitter_callback(synchronizer, "error", self.on_error)

        self.exc_manager.add(YaDiskError, self.on_disk_error)
        self.exc_manager.add(BaseException, self.on_exception)

    def on_started(self, event):
        print("Synchronizer: started")

    def on_finished(self, event):
        print("Synchronizer: finished")

    def on_next_target(self, event, target):
        print("Next target: [%s -> %s]" % (target.local, target.remote))

    def on_worker_started(self, event, worker):
        if isinstance(worker, ScanWorker):
            worker.add_receiver(self.scan_worker_receiver)
        else:
            worker.add_receiver(self.worker_receiver)

    def on_entered_stage(self, event, stage):
        synchronizer = event.emitter
        target = synchronizer.cur_target

        if stage == "scan" and not target.enable_scan:
            return

        if stage == "check" and target.skip_integrity_check:
            return

        print("Synchronizer: entered stage %r" % stage)

    def on_exited_stage(self, event, stage):
        synchronizer = event.emitter
        target = synchronizer.cur_target

        if stage == "scan":
            if target.status not in ("failed", "suspended"):
                print_diffs(self.env, synchronizer.encsync, target)

                ask = self.env.get("ask", False)
                no_diffs = self.env.get("no_diffs", False)

                if ask and not no_diffs:
                    action = ask_continue(synchronizer)

                    while action == "view":
                        view_diffs(self.env, synchronizer.encsync, target)
                        action = ask_continue(synchronizer)

                    if action == "stop":
                        synchronizer.stop()
                    elif action == "skip":
                        target.change_status("suspended")
        elif stage == "check" and target.skip_integrity_check:
            return

        print("Synchronizer exited stage %r" % stage)

    def on_error(self, event, exc):
        self.exc_manager.handle(exc, event.emitter)

    def on_disk_error(self, exc, synchronizer):
        target = synchronizer.cur_target
        print("[%s -> %s]: error: %s: %s" % (target.local, target.remote,
                                             exc.error_type, exc))

    def on_exception(self, exc, synchronizer):
        traceback.print_exc()

class TargetReceiver(EventHandler):
    def __init__(self, env):
        EventHandler.__init__(self)

        self.scan_target_receiver = ScanTargetReceiver(env)

        self.add_callback("status_changed", self.on_status_changed)
        self.add_callback("local_scan", self.on_local_scan)
        self.add_callback("local_scan_finished", self.on_local_scan_finished)
        self.add_callback("local_scan_failed", self.on_local_scan_failed)
        self.add_callback("remote_scan", self.on_remote_scan)
        self.add_callback("remote_scan_finished", self.on_remote_scan_finished)
        self.add_callback("remote_scan_failed", self.on_remote_scan_failed)
        self.add_callback("integrity_check", self.on_integrity_check)
        self.add_callback("integrity_check_finished", self.on_integrity_check_finished)
        self.add_callback("integrity_check_failed", self.on_integrity_check_failed)
        self.add_callback("diffs_started", self.on_diffs_started)
        self.add_callback("diffs_failed", self.on_diffs_failed)
        self.add_callback("diffs_finished", self.on_diffs_finished)

    def on_status_changed(self, event):
        target = event["emitter"]
        status = target.status

        if status in ("finished", "failed", "suspended"):
            print("Target [%s -> %s]: %s" % (target.local, target.remote, status))

        if status in ("finished", "failed"):
            print_target_totals(target)

    def on_local_scan(self, event, scan_target):
        target = event["emitter"]

        print("[%s -> %s]: local scan" % (target.local, target.remote))

        scan_target.add_receiver(self.scan_target_receiver)

    def on_local_scan_finished(self, event, scan_target):
        target = event["emitter"]
        print("[%s -> %s]: local scan: finished" % (target.local, target.remote))

    def on_local_scan_failed(self, event, scan_target):
        target = event["emitter"]
        print("[%s -> %s]: local scan: failed" % (target.local, target.remote))

    def on_remote_scan(self, event, scan_target):
        target = event["emitter"]

        print("[%s -> %s]: remote scan" % (target.local, target.remote))
        scan_target.add_receiver(self.scan_target_receiver)

    def on_remote_scan_finished(self, event, scan_target):
        target = event["emitter"]
        print("[%s -> %s]: remote scan: finished" % (target.local, target.remote))

    def on_remote_scan_failed(self, event, scan_target):
        target = event["emitter"]
        print("[%s -> %s]: remote scan: failed" % (target.local, target.remote))

    def on_integrity_check(self, event):
        target = event["emitter"]
        print("[%s -> %s]: integrity check" % (target.local, target.remote))

    def on_integrity_check_finished(self, event):
        target = event["emitter"]
        print("[%s -> %s]: integrity check: finished" % (target.local, target.remote))

    def on_integrity_check_failed(self, event):
        target = event["emitter"]
        print("[%s -> %s]: integrity check: failed" % (target.local, target.remote))

    def on_diffs_started(self, event):
        target = event.emitter

        print("[%s -> %s]: building the difference table" % (target.local, target.remote))

    def on_diffs_failed(self, event):
        target = event.emitter

        print("[%s -> %s]: failed to build the difference table" % (target.local, target.remote))

    def on_diffs_finished(self, event):
        target = event.emitter

        print("[%s -> %s]: finished building the difference table" % (target.local, target.remote))

class WorkerReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.task_receiver = TaskReceiver()

        self.add_callback("next_task", self.on_next_task)
        self.add_callback("error", self.on_error)

        self.exc_manager = ExceptionManager()

        self.exc_manager.add(YaDiskError, self.on_disk_error)
        self.exc_manager.add(TooLongFilenameError, self.on_too_long_filename)
        self.exc_manager.add(BaseException, self.on_exception)

    def on_next_task(self, event, task):
        msg = get_progress_str(task) + ": "

        if task.task_type == "new":
            if task.type == "f":
                msg += "uploading file"
            elif task.type == "d":
                msg += "creating remote directory"
        elif task.task_type == "rm":
            if task.type == "f":
                msg += "removing remote file"
            elif task.type == "d":
                msg += "removing remote directory"
        elif task.task_type == "rmdup":
            if task.type == "f":
                msg += "removing remote file duplicate"
            elif task.type == "f":
                msg += "removing remote directory duplicate"

        print(msg)

        task.add_receiver(self.task_receiver)

    def on_error(self, event, exc):
        self.exc_manager.handle(exc, event.emitter)

    def on_disk_error(self, exc, worker):
        progress_str = get_progress_str(worker.cur_task)
        print("%s: error: %s: %s" % (progress_str, exc.error_type, exc))

    def on_too_long_filename(self, exc, worker):
        progress_str = get_progress_str(worker.cur_task)
        print("%s: error: too long filename (>= 160)" % progress_str)

    def on_exception(self, exc, worker):
        traceback.print_exc()

class TaskReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.add_callback("uploaded_changed", self.on_uploaded_changed)
        self.add_callback("status_changed", self.on_status_changed)

        self.last_uploaded_percents = {}

    def on_status_changed(self, event):
        task = event["emitter"]

        status = task.status

        if status in (None, "pending"):
            return

        progress_str = get_progress_str(task)

        print(progress_str + ": %s" % status)

    def on_uploaded_changed(self, event):
        task = event["emitter"]
        uploaded, size = task.uploaded, task.size

        try:
            uploaded_percent = float(uploaded) / size * 100.0
        except ZeroDivisionError:
            uploaded_percent = 100.0

        last_uploaded = self.last_uploaded_percents.get(task, 0.0)

        # Change can be negative due to retries
        if abs(uploaded_percent - last_uploaded) < 25.0 and uploaded_percent < 100.0:
            return

        self.last_uploaded_percents[task] = uploaded_percent

        progress_str = get_progress_str(task)

        print(progress_str + ": uploaded %6.2f%%" % uploaded_percent)

def do_sync(env, names):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    common.cleanup_filelists(env)

    no_scan = env.get("no_scan", False)
    no_check = env.get("no_check", False)
    no_choice = env.get("no_choice", False)
    ask = env.get("ask", False)

    names = list(names)

    if env.get("all", False):
        for target in encsync.targets:
            names.append(target["name"])

    if len(names) == 0:
        show_error("Error: no targets given")
        return 1

    n_sync_workers = env.get("n_workers", encsync.sync_threads)
    n_scan_workers = env.get("n_workers", encsync.scan_threads)
    no_journal = env.get("no_journal", False)

    synchronizer = Synchronizer(encsync,
                                env["db_dir"],
                                n_sync_workers,
                                n_scan_workers,
                                enable_journal=not no_journal)

    synchronizer.set_speed_limit(encsync.upload_limit)

    with GenericSignalManager(synchronizer):
        synchronizer_receiver = SynchronizerReceiver(env, synchronizer)
        synchronizer.add_receiver(synchronizer_receiver)

        target_receiver = TargetReceiver(env)

        targets = []

        for name in names:
            local_path = None
            remote_path = None
            for i in encsync.targets:
                if i["name"] == name:
                    local_path = os.path.abspath(os.path.expanduser(i["local"]))
                    remote_path = common.prepare_remote_path(i["remote"])
                    break

            if local_path is None and remote_path is None:
                show_error("Error: unknown target %r" % (name,))
                return 1

            target = SyncTarget(synchronizer, name, local_path, remote_path)
            target.enable_scan = not no_scan
            target.skip_integrity_check = no_check
            targets.append(target)

        if ask and not no_choice:
            targets = ask_target_choice(targets)

        for target in targets:
            synchronizer.add_target(target)
            target.add_receiver(target_receiver)

        print("Targets to sync:")
        for target in targets:
            print("[%s -> %s]" % (target.local, target.remote))

        synchronizer.start()
        synchronizer.join()

        if any(i.status not in ("finished", "suspended") for i in targets):
            return 1

        if synchronizer.stopped:
            return 1

        return 0
