#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import traceback

from ..Downloader import Downloader
from ..Event.EventHandler import EventHandler

from . import common
from .common import show_error, get_progress_str, make_size_readable
from .SignalManagers import GenericSignalManager

def print_target_totals(target):
    n_finished = target.progress["finished"]
    n_failed = target.progress["failed"]
    n_total = target.total_children
    downloaded = make_size_readable(target.downloaded)

    local, remote = target.local, target.remote

    print("[%s <- %s]: %d tasks in total" % (local, remote, n_finished))
    print("[%s <- %s]: %d tasks successful" % (local, remote, n_total))
    print("[%s <- %s]: %d tasks failed" % (local, remote, n_failed))
    print("[%s <- %s]: %s downloaded" % (local, remote, downloaded))

class DownloaderReceiver(EventHandler):
    def __init__(self, scanner):
        EventHandler.__init__(self)

        self.worker_receiver = WorkerReceiver()

        self.add_emitter_callback(scanner, "started", self.on_started)
        self.add_emitter_callback(scanner, "finished", self.on_finished)
        self.add_emitter_callback(scanner, "next_target", self.on_next_target)
        self.add_emitter_callback(scanner, "worker_started", self.on_worker_started)
        self.add_emitter_callback(scanner, "error", self.on_error)

    def on_started(self, event):
        print("Downloader: started")

    def on_finished(self, event):
        print("Downloader: finished")

    def on_next_target(self, event, target):
        print("Next target: [%s <- %s]" % (target.local, target.remote))

    def on_worker_started(self, event, worker):
        worker.add_receiver(self.worker_receiver)

    def on_error(self, event, exception):
        traceback.print_exc()

class TargetReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.add_callback("status_changed", self.on_status_changed)

    def on_status_changed(self, event):
        target = event["emitter"]

        local, remote, status = target.local, target.remote, target.status

        if status in ("finished", "failed", "suspended"):
            print("Target [%s <- %s]: %s" % (local, remote, status))

        if status in ("finished", "failed",):
            print_target_totals(target)

class WorkerReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.task_receiver = TaskReceiver()

        self.add_callback("next_task", self.on_next_task)
        self.add_callback("error", self.on_error)

    def on_next_task(self, event, task):
        progress_str = get_progress_str(task)

        print(progress_str + ": downloading")

        task.add_receiver(self.task_receiver)

    def on_error(self, event, exception):
        traceback.print_exc()

class TaskReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.add_callback("status_changed", self.on_status_changed)
        self.add_callback("downloaded_changed", self.on_downloaded_changed)
        self.add_callback("obtain_link_failed", self.on_obtain_link_failed)

        self.last_download_percents = {}

    def on_status_changed(self, event):
        task = event["emitter"]

        if task.status in ("finished", "failed", "suspended"):
            progress_str = get_progress_str(task)
            print(progress_str + ": %s" % task.status)

    def on_downloaded_changed(self, event):
        task = event["emitter"]

        try:
            downloaded_percent = float(task.downloaded) / task.size * 100.0
        except ZeroDivisionError:
            downloaded_percent = 100.0

        last_percent = self.last_download_percents.get(task, 0.0)

        # Change can be negative due to retries
        if abs(downloaded_percent - last_percent) < 25.0 and downloaded_percent < 100.0:
            return

        self.last_download_percents[task] = downloaded_percent

        progress_str = get_progress_str(task)

        print(progress_str + ": downloaded %6.2f%%" % downloaded_percent)

    def on_obtain_link_failed(self, event):
        task = event["emitter"]

        progress_str = get_progress_str(task)

        print(progress_str + ": failed to obtain download link")

def download(env, paths):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    n_workers = env.get("n_workers", encsync.download_threads)

    downloader = Downloader(encsync, env["config_dir"], n_workers)
    downloader.set_speed_limit(encsync.download_limit)

    with GenericSignalManager(downloader):
        downloader_receiver = DownloaderReceiver(downloader)
        downloader.add_receiver(downloader_receiver)

        target_receiver = TargetReceiver()

        targets = []

        if len(paths) == 1:
            local = os.getcwd()
        else:
            local = paths.pop()

        for path in paths:
            path, path_type = common.recognize_path(path)

            path = common.prepare_remote_path(path)

            prefix = encsync.find_encrypted_dir(path)

            if prefix is None:
                show_error("%r does not appear to be encrypted" % path)
                return 1

            target = downloader.add_download(prefix, path, local)
            target.add_receiver(target_receiver)
            targets.append(target)

        downloader.start()
        downloader.join()

        if any(i.status != "finished" for i in targets):
            return 1

    return 0
