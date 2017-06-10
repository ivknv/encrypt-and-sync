#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import common
from .common import show_error, get_progress_str

from ..Synchronizer import Synchronizer
from ..Event.EventHandler import EventHandler

def print_target_totals(target):
    n_finished = target.progress["finished"] 
    n_failed = target.progress["failed"]
    n_total = target.total_children

    print("[%s -> %s]: %d tasks in total" % (target.local, target.remote, n_total))
    print("[%s -> %s]: %d tasks successful" % (target.local, target.remote, n_finished))
    print("[%s -> %s]: %d tasks failed" % (target.local, target.remote, n_failed))

class SynchronizerReceiver(EventHandler):
    def __init__(self, synchronizer):
        EventHandler.__init__(self)

        self.worker_receiver = WorkerReceiver()

        self.synchronizer = synchronizer

        self.add_emitter_callback(synchronizer, "started", self.on_started)
        self.add_emitter_callback(synchronizer, "finished", self.on_finished)
        self.add_emitter_callback(synchronizer, "next_target", self.on_next_target)
        self.add_emitter_callback(synchronizer, "worker_started", self.on_worker_started)
        self.add_emitter_callback(synchronizer, "entered_stage", self.on_entered_stage)
        self.add_emitter_callback(synchronizer, "exited_stage", self.on_exited_stage)

    def on_started(self, event):
        print("Synchronizer: started")

    def on_finished(self, event):
        print("Synchronizer: finished")

    def on_next_target(self, event, target):
        print("Next target: [%s -> %s]" % (target.local, target.remote))

    def on_worker_started(self, event, worker):
        worker.add_receiver(self.worker_receiver)

    def on_entered_stage(self, event, stage):
        target = self.synchronizer.cur_target
        if stage == "scan" and not target.enable_scan:
            return

        if stage == "check" and target.skip_integrity_check:
            return

        print("Synchronizer: entered stage %r" % stage)

    def on_exited_stage(self, event, stage):
        target = self.synchronizer.cur_target
        if stage == "scan" and not target.enable_scan:
            return

        if stage == "check" and target.skip_integrity_check:
            return

        print("Synchronizer exited stage %r" % stage)

class TargetReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.add_callback("status_changed", self.on_status_changed)

    def on_status_changed(self, event):
        target = event["emitter"]
        status = target.status

        if status in ("finished", "failed", "suspended"):
            print("Target [%s -> %s]: %s" % (target.local, target.remote, status))

        if status in ("finished", "failed"):
            print_target_totals(target)

class WorkerReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.task_receiver = TaskReceiver()

        self.add_callback("next_task", self.on_next_task)

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

        print(msg)

        task.add_receiver(self.task_receiver)

class TaskReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.add_callback("uploaded_changed", self.on_uploaded_changed)
        self.add_callback("status_changed", self.on_status_changed)
        self.add_callback("filename_too_long", self.on_filename_too_long)

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

    def on_filename_too_long(self, event):
        task = event["emitter"]

        progress_str = get_progress_str(task)

        print(progress_str + ": filename is too long (>= 160)")

def do_sync(env, paths, n_workers):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    synchronizer = Synchronizer(env["encsync"], n_workers)
    synchronizer_receiver = SynchronizerReceiver(synchronizer)
    synchronizer.add_receiver(synchronizer_receiver)

    target_receiver = TargetReceiver()

    targets = []

    for path1, path2 in zip(paths[::2], paths[1::2]):
        path1, path1_type = common.recognize_path(path1)
        path2, path2_type = common.recognize_path(path2)

        if path1_type == path2_type:
            show_error("Error: expected a pair of both local and remote paths")
            return 1

        if path1_type == "local":
            local, remote = path1, path2
        else:
            local, remote = path2, path1

        local = os.path.realpath(os.path.expanduser(local))
        remote = common.prepare_remote_path(remote)

        target = synchronizer.add_new_target(False, local, remote, None)
        target.skip_integrity_check = True
        target.add_receiver(target_receiver)
        targets.append(target)

    synchronizer.start()
    synchronizer.join()

    if any(i.status != "finished" for i in targets):
        return 1

    return 0
