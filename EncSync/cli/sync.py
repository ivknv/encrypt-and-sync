#!/usr/bin/env python
# -*- coding: utf-8 -*-

import traceback

from yadisk.exceptions import YaDiskError

from . import common
from .common import show_error, get_progress_str
from .scan import ScannerReceiver
from .remove_duplicates import DuplicateRemoverReceiver

from ..Synchronizer import Synchronizer
from ..Scanner import Scanner
from ..DuplicateRemover import DuplicateRemover
from ..Event.EventHandler import EventHandler
from ..FileList import DuplicateList
from ..DiffList import DiffList
from .SignalManagers import GenericSignalManager
from .parse_choice import interpret_choice
from ..ExceptionManager import ExceptionManager
from ..Synchronizer.Exceptions import TooLongFilenameError

def ask_target_choice(targets):
    for i, target in enumerate(targets):
        print("[%d] [%s]" % (i + 1, target.name))

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

def count_duplicates(env, target_storage):
    duplist = DuplicateList(target_storage.storage.name, env["db_dir"])
    duplist.create()

    return duplist.get_children_count(target_storage.prefix)

def select_duplicates(env, target_storage):
    duplist = DuplicateList(target_storage.storage.name, env["db_dir"])
    duplist.create()

    return duplist.find_children(target_storage.prefix)

def print_diffs(env, encsync, target):
    difflist = DiffList(encsync, env["db_dir"])
    name = target.name

    n_duplicates = 0

    if target.src.encrypted:
        n_duplicates += count_duplicates(env, target.src)

    if target.dst.encrypted:
        n_duplicates += count_duplicates(env, target.dst)

    n_rm = difflist.count_rm_differences(name)
    n_dirs = difflist.count_dirs_differences(name)
    n_new_files = difflist.count_new_file_differences(name)
    n_update = difflist.count_update_differences(name)

    print("[%s]: %d duplicate removals" % (name, n_duplicates))
    print("[%s]: %d removals" % (name, n_rm))
    print("[%s]: %d new directories" % (name, n_dirs))
    print("[%s]: %d new files to upload" % (name, n_new_files))
    print("[%s]: %d files to update" % (name, n_update))

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

def view_diffs(env, encsync, target):
    funcs = {"r":  view_rm_diffs,       "d":  view_dirs_diffs,
             "f":  view_new_file_diffs, "u":  view_update_diffs,
             "du": view_duplicates}

    s = "What differences? [(r)m/(d)irs/new (f)iles/(u)pdates/(du)plicates/(s)top]: "

    while True:
        answer = input(s).lower()

        if answer in funcs.keys():
            funcs[answer](env, encsync, target)
        elif answer == "s":
            break

def view_rm_diffs(env, encsync, target):
    difflist = DiffList(encsync, env["db_dir"])

    diffs = difflist.select_rm_differences(target.name)

    print("Removals:")
    for diff in diffs:
        print("  %s %s" % (diff["node_type"], diff["path"]))

def view_dirs_diffs(env, encsync, target):
    difflist = DiffList(encsync, env["db_dir"])

    diffs = difflist.select_dirs_differences(target.name)

    print("New directories:")
    for diff in diffs:
        print("  %s" % (diff["path"],))

def view_new_file_diffs(env, encsync, target):
    difflist = DiffList(encsync, env["db_dir"])

    diffs = difflist.select_new_file_differences(target.name)

    print("New files to upload:")
    for diff in diffs:
        print("  %s" % (diff["path"],))

def view_update_diffs(env, encsync, target):
    difflist = DiffList(encsync, env["db_dir"])

    diffs = difflist.select_update_differences(target.name)

    print("Files to update:")
    for diff in diffs:
        print("  %s" % (diff["path"],))

def view_duplicates(env, encsync, target):
    if target.src.encrypted:
        duplicates = select_duplicates(env, target.src)

        for duplicate in duplicates:
            print("  %s %s" % (duplicate[0], duplicate[2]))

    if target.dst.encrypted:
        duplicates = select_duplicates(env, target.dst)

        for duplicate in duplicates:
            print("  %s %s" % (duplicate[0], duplicate[2]))

def print_target_totals(target):
    n_finished = target.progress["finished"]
    n_failed = target.progress["failed"]
    n_total = target.total_children

    print("[%s]: %d tasks in total" % (target.name, n_total))
    print("[%s]: %d tasks successful" % (target.name, n_finished))
    print("[%s]: %d tasks failed" % (target.name, n_failed))

class SynchronizerReceiver(EventHandler):
    def __init__(self, env, synchronizer):
        EventHandler.__init__(self)

        self.worker_receiver = WorkerReceiver()
        self.target_receiver = TargetReceiver(env)
        self.env = env

        self.exc_manager = ExceptionManager()

        self.add_emitter_callback(synchronizer, "started", self.on_started)
        self.add_emitter_callback(synchronizer, "finished", self.on_finished)
        self.add_emitter_callback(synchronizer, "next_target", self.on_next_target)
        self.add_emitter_callback(synchronizer, "worker_starting", self.on_worker_starting)
        self.add_emitter_callback(synchronizer, "error", self.on_error)

        self.exc_manager.add(YaDiskError, self.on_disk_error)
        self.exc_manager.add(BaseException, self.on_exception)

    def on_started(self, event):
        print("Synchronizer: started")

    def on_finished(self, event):
        print("Synchronizer: finished")

    def on_next_target(self, event, target):
        target.add_receiver(self.target_receiver)
        print("Next target: [%s]" % (target.name,))

    def on_worker_starting(self, event, worker):
        if isinstance(worker, Scanner):
            worker.add_receiver(ScannerReceiver(self.env, worker))
        elif isinstance(worker, DuplicateRemover):
            worker.add_receiver(DuplicateRemoverReceiver(self.env, worker, False))
        else:
            worker.add_receiver(self.worker_receiver)

    def on_error(self, event, exc):
        self.exc_manager.handle(exc, event.emitter)

    def on_disk_error(self, exc, synchronizer):
        target = synchronizer.cur_target
        print("[%s]: error: %s: %s" % (target.name, exc.error_type, exc))

    def on_exception(self, exc, synchronizer):
        traceback.print_exc()

class TargetReceiver(EventHandler):
    def __init__(self, env):
        EventHandler.__init__(self)

        self.env = env

        self.add_callback("status_changed", self.on_status_changed)
        self.add_callback("integrity_check", self.on_integrity_check)
        self.add_callback("integrity_check_finished", self.on_integrity_check_finished)
        self.add_callback("integrity_check_failed", self.on_integrity_check_failed)
        self.add_callback("diffs_started", self.on_diffs_started)
        self.add_callback("diffs_failed", self.on_diffs_failed)
        self.add_callback("diffs_finished", self.on_diffs_finished)
        self.add_callback("entered_stage", self.on_entered_stage)
        self.add_callback("exited_stage", self.on_exited_stage)

    def on_status_changed(self, event):
        target = event["emitter"]
        status = target.status

        if status in ("finished", "failed", "suspended"):
            print("[%s]: %s" % (target.name, status))

        if status in ("finished", "failed"):
            print_target_totals(target)

    def on_integrity_check(self, event):
        target = event["emitter"]
        print("[%s]: integrity check" % (target.name,))

    def on_integrity_check_finished(self, event):
        target = event["emitter"]
        print("[%s]: integrity check: finished" % (target.name,))

    def on_integrity_check_failed(self, event):
        target = event["emitter"]
        print("[%s]: integrity check: failed" % (target.name,))

    def on_diffs_started(self, event):
        target = event.emitter

        print("[%s]: building the difference table" % (target.name,))

    def on_diffs_failed(self, event):
        target = event.emitter

        print("[%s]: failed to build the difference table" % (target.name,))

    def on_diffs_finished(self, event):
        target = event.emitter

        print("[%s]: finished building the difference table" % (target.name,))

    def on_entered_stage(self, event, stage):
        target = event.emitter

        if stage == "scan" and not target.enable_scan:
            return

        if stage == "check" and target.skip_integrity_check:
            return

        print("[%s]: entered stage %r" % (target.name, stage))

    def on_exited_stage(self, event, stage):
        target = event.emitter

        if stage == "scan":
            if target.status not in ("failed", "suspended"):
                print_diffs(self.env, target.encsync, target)

                ask = self.env.get("ask", False)
                no_diffs = self.env.get("no_diffs", False)

                if ask and not no_diffs:
                    action = ask_continue()

                    while action == "view":
                        view_diffs(self.env, target.encsync, target)
                        action = ask_continue()

                    if action == "stop":
                        target.synchronizer.stop()
                    elif action == "skip":
                        target.change_status("suspended")

                if not target.enable_scan:
                    return
        elif stage == "check" and target.skip_integrity_check:
            return

        print("[%s]: exited stage %r" % (target.name, stage))

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
    choose_targets = env.get("choose_targets", False)
    ask = env.get("ask", False)

    names = list(names)

    if env.get("all", False):
        names.extend(sorted(encsync.targets.keys()))

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

        targets = []

        for name in names:
            target = synchronizer.make_target(name, not no_scan)
            target.skip_integrity_check = no_check
            targets.append(target)

        if (ask and env.get("all", False)) or choose_targets:
            targets = ask_target_choice(targets)

        for target in targets:
            synchronizer.add_target(target)

        print("Targets to sync:")
        for target in targets:
            print("[%s]" % (target.name,))

        synchronizer.start()
        synchronizer.join()

        if any(i.status not in ("finished", "suspended") for i in targets):
            return 1

        if synchronizer.stopped:
            return 1

        return 0
