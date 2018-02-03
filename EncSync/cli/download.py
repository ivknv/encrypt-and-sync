#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import traceback

from yadisk.exceptions import YaDiskError

from .. import Paths
from ..Downloader import Downloader
from ..Downloader.Exceptions import NotFoundInDBError
from ..Event.EventHandler import EventHandler

from . import common
from .common import show_error, get_progress_str, make_size_readable
from .SignalManagers import GenericSignalManager
from ..ExceptionManager import ExceptionManager

def print_target_totals(target):
    n_finished = target.progress["finished"]
    n_failed = target.progress["failed"]
    n_total = target.total_children
    downloaded = make_size_readable(target.downloaded)

    dst_path, src_path = target.dst_path, target.src_path
    dst_path = "%s://%s" % (target.dst.storage.name, dst_path)
    src_path = "%s://%s" % (target.src.storage.name, src_path)

    print("[%s <- %s]: %d tasks in total" % (dst_path, src_path, n_total))
    print("[%s <- %s]: %d tasks successful" % (dst_path, src_path, n_finished))
    print("[%s <- %s]: %d tasks failed" % (dst_path, src_path, n_failed))
    print("[%s <- %s]: %s downloaded" % (dst_path, src_path, downloaded))

class DownloaderReceiver(EventHandler):
    def __init__(self, downloader):
        EventHandler.__init__(self)

        self.worker_receiver = WorkerReceiver()

        self.downloader = downloader

        self.add_emitter_callback(downloader, "started", self.on_started)
        self.add_emitter_callback(downloader, "finished", self.on_finished)
        self.add_emitter_callback(downloader, "next_target", self.on_next_target)
        self.add_emitter_callback(downloader, "worker_starting", self.on_worker_starting)
        self.add_emitter_callback(downloader, "error", self.on_error)

        self.exc_manager = ExceptionManager()

        self.exc_manager.add(YaDiskError, self.on_disk_error)
        self.exc_manager.add(NotFoundInDBError, self.on_not_found_error)
        self.exc_manager.add(BaseException, self.on_exception)

    def on_started(self, event):
        print("Downloader: started")

    def on_finished(self, event):
        print("Downloader: finished")

    def on_next_target(self, event, target):
        src_path = "%s://%s" % (target.src.storage.name, target.src_path)
        dst_path = "%s://%s" % (target.dst.storage.name, target.dst_path)
        print("Next target: [%s <- %s]" % (dst_path, src_path))

    def on_worker_starting(self, event, worker):
        worker.add_receiver(self.worker_receiver)

    def on_error(self, event, exc):
        self.exc_manager.handle(exc)

    def on_disk_error(self, exc):
        target = self.downloader.cur_target

        dst_path, src_path = target.dst_path, target.src_path
        dst_path = "%s://%s" % (target.dst.storage.name, dst_path)
        src_path = "%s://%s" % (target.src.storage.name, src_path)

        print("[%s <- %s]: error: %s: %s" % (target.dst_path, target.src_path,
                                             exc.error_type, exc))

    def on_not_found_error(self, exc):
        target = self.downloader.cur_target

        dst_path = "%s://%s" % (target.dst.storage.name, target.dst_path)
        src_path = "%s://%s" % (target.src.storage.name, target.src_path)

        print("[%s <- %s]: error: %s" % (dst_path, src_path, exc))

    def on_exception(self, exception):
        traceback.print_exc()

class TargetReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.add_callback("status_changed", self.on_status_changed)

    def on_status_changed(self, event):
        target = event["emitter"]

        dst_path = "%s://%s" % (target.dst.storage.name, target.dst_path)
        src_path = "%s://%s" % (target.src.storage.name, target.src_path)
        status = target.status

        if status != "pending":
            print("[%s <- %s]: %s" % (dst_path, src_path, status))

        if status in ("finished", "failed",):
            print_target_totals(target)

class WorkerReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.task_receiver = TaskReceiver()

        self.add_callback("next_task", self.on_next_task)
        self.add_callback("error", self.on_error)

        self.exc_manager = ExceptionManager()

        self.exc_manager.add(YaDiskError, self.on_disk_error)
        self.exc_manager.add(BaseException, self.on_exception)

    def on_next_task(self, event, task):
        progress_str = get_progress_str(task)

        print(progress_str + ": downloading")

        task.add_receiver(self.task_receiver)

    def on_error(self, event, exc):
        self.exc_manager.handle(exc, event.emitter)

    def on_disk_error(self, exc, worker):
        progress_str = get_progress_str(worker.cur_task)
        print("%s: error: %s: %s" % (progress_str, exc.error_type, exc))

    def on_exception(self, exc, worker):
        traceback.print_exc()

class TaskReceiver(EventHandler):
    def __init__(self):
        EventHandler.__init__(self)

        self.add_callback("status_changed", self.on_status_changed)
        self.add_callback("downloaded_changed", self.on_downloaded_changed)
        self.add_callback("uploaded_changed", self.on_uploaded_changed)

        self.last_download_percents = {}
        self.last_upload_percents = {}

    def on_status_changed(self, event):
        task = event["emitter"]

        if task.status != "pending":
            progress_str = get_progress_str(task)
            print(progress_str + ": %s" % task.status)

    def on_downloaded_changed(self, event):
        task = event["emitter"]

        try:
            downloaded_percent = float(task.downloaded) / task.download_size * 100.0
        except ZeroDivisionError:
            downloaded_percent = 100.0

        last_percent = self.last_download_percents.get(task, 0.0)

        # Change can be negative due to retries
        if abs(downloaded_percent - last_percent) < 25.0 and downloaded_percent < 100.0:
            return

        self.last_download_percents[task] = downloaded_percent

        progress_str = get_progress_str(task)

        print(progress_str + ": received %6.2f%%" % downloaded_percent)

    def on_uploaded_changed(self, event):
        task = event["emitter"]

        try:
            uploaded_percent = float(task.uploaded) / task.upload_size * 100.0
        except ZeroDivisionError:
            uploaded_percent = 100.0

        last_percent = self.last_upload_percents.get(task, 0.0)

        # Change can be negative due to retries
        if abs(uploaded_percent - last_percent) < 25.0 and uploaded_percent < 100.0:
            return

        self.last_upload_percents[task] = uploaded_percent

        progress_str = get_progress_str(task)

        print(progress_str + ": sent %6.2f%%" % uploaded_percent)

def download(env, paths):
    config, ret = common.make_config(env)

    if config is None:
        return ret

    n_workers = env.get("n_workers", config.download_threads)

    downloader = Downloader(config, env["db_dir"], n_workers)
    downloader.upload_limit = config.upload_limit
    downloader.download_limit = config.download_limit

    with GenericSignalManager(downloader):
        downloader_receiver = DownloaderReceiver(downloader)
        downloader.add_receiver(downloader_receiver)

        target_receiver = TargetReceiver()

        targets = []

        if len(paths) == 1:
            dst_path = Paths.from_sys(os.getcwd())
        else:
            dst_path = paths.pop()

        dst_path, dst_path_type = common.recognize_path(dst_path)

        if dst_path_type == "local":
            dst_path = Paths.from_sys(os.path.abspath(Paths.to_sys(dst_path)))
        else:
            dst_path = Paths.join_properly("/", dst_path)

        for src_path in paths:
            src_path, src_path_type = common.recognize_path(src_path)

            if src_path_type == "local":
                src_path = Paths.from_sys(os.path.abspath(Paths.to_sys(src_path)))
            else:
                src_path = Paths.join_properly("/", src_path)

            target = downloader.add_download(src_path_type, src_path,
                                             dst_path_type, dst_path)
            target.add_receiver(target_receiver)
            targets.append(target)

        downloader.start()
        downloader.join()

        if any(i.status not in ("finished", "skipped") for i in targets):
            return 1

        if downloader.stopped:
            return 1

    return 0
