#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import traceback

from yadisk.exceptions import YaDiskError

from .. import Paths
from ..Downloader import Downloader
from ..Downloader.Exceptions import NotFoundInDBError
from ..Event.Receiver import Receiver

from . import common
from .authenticate_storages import authenticate_storages
from .common import show_error, get_progress_str, make_size_readable
from .SignalManagers import GenericSignalManager
from ..ExceptionManager import ExceptionManager

def print_target_totals(target):
    n_finished = target.progress["finished"] + target.progress["skipped"]
    n_failed = target.progress["failed"]
    n_total = target.total_children
    downloaded = make_size_readable(target.downloaded)

    dst_path, src_path = target.dst_path, target.src_path
    dst_path = "%s://%s" % (target.dst_storage_name, dst_path)
    src_path = "%s://%s" % (target.src_storage_name, src_path)

    print("[%s <- %s]: %d tasks in total" % (dst_path, src_path, n_total))
    print("[%s <- %s]: %d tasks successful" % (dst_path, src_path, n_finished))
    print("[%s <- %s]: %d tasks failed" % (dst_path, src_path, n_failed))
    print("[%s <- %s]: %s downloaded" % (dst_path, src_path, downloaded))

class DownloaderExceptionManager(ExceptionManager):
    def __init__(self, downloader):
        ExceptionManager.__init__(self)

        self.downloader = downloader

        def on_disk_error(exc, worker):
            target = downloader.cur_target

            dst_path, src_path = target.dst_path, target.src_path
            dst_path = "%s://%s" % (target.dst_storage_name, dst_path)
            src_path = "%s://%s" % (target.src_storage_name, src_path)

            show_error("[%s <- %s]: error: %s: %s" % (target.dst_path, target.src_path,
                                                      exc.error_type, exc))

        def on_not_found_error(exc, worker):
            target = self.downloader.cur_target

            dst_path = "%s://%s" % (target.dst_storage_name, target.dst_path)
            src_path = "%s://%s" % (target.src_storage_name, target.src_path)

            show_error("[%s <- %s]: error: %s" % (dst_path, src_path, exc))

        def on_exception(exc, worker):
            traceback.print_exc()

        self.add(YaDiskError, on_disk_error)
        self.add(NotFoundInDBError, on_not_found_error)
        self.add(Exception, on_exception)

class DownloaderReceiver(Receiver):
    def __init__(self, downloader):
        Receiver.__init__(self)

        self.worker_receiver = WorkerReceiver(downloader)

        self.downloader = downloader

        self.exc_manager = DownloaderExceptionManager(downloader)

    def on_started(self, event):
        print("Downloader: started")

    def on_finished(self, event):
        print("Downloader: finished")

    def on_next_target(self, event, target):
        src_path = "%s://%s" % (target.src_storage_name, target.src_path)
        dst_path = "%s://%s" % (target.dst_storage_name, target.dst_path)
        print("Next target: [%s <- %s]" % (dst_path, src_path))

    def on_worker_starting(self, event, worker):
        worker.add_receiver(self.worker_receiver)

    def on_error(self, event, exc):
        self.exc_manager.handle(exc, event.emitter)

class TargetReceiver(Receiver):
    def __init__(self):
        Receiver.__init__(self)

    def on_status_changed(self, event):
        target = event["emitter"]

        status = target.status

        if status != "pending":
            dst_path = "%s://%s" % (target.dst_storage_name, target.dst_path)
            src_path = "%s://%s" % (target.src_storage_name, target.src_path)

            print("[%s <- %s]: %s" % (dst_path, src_path, status))

        if status in ("finished", "failed",):
            print_target_totals(target)

class WorkerReceiver(Receiver):
    def __init__(self, downloader):
        Receiver.__init__(self)

        self.task_receiver = TaskReceiver()

        self.exc_manager = DownloaderExceptionManager(downloader)

    def on_next_task(self, event, task):
        progress_str = get_progress_str(task)

        print(progress_str + ": downloading")

        task.add_receiver(self.task_receiver)

    def on_error(self, event, exc):
        self.exc_manager.handle(exc, event.emitter)

class TaskReceiver(Receiver):
    def __init__(self):
        Receiver.__init__(self)

        self.last_download_percents = {}
        self.last_upload_percents = {}

    def on_status_changed(self, event):
        task = event["emitter"]

        if task.status in ("pending", None):
            return

        progress_str = get_progress_str(task)
        print(progress_str + ": %s" % task.status)

        self.last_download_percents.pop(task.src_path, None)
        self.last_upload_percents.pop(task.src_path, None)

    def on_downloaded_changed(self, event):
        task = event["emitter"]

        try:
            downloaded_percent = float(task.downloaded) / task.download_size * 100.0
        except ZeroDivisionError:
            downloaded_percent = 100.0

        last_percent = self.last_download_percents.get(task.src_path, 0.0)

        # Change can be negative due to retries
        if abs(downloaded_percent - last_percent) < 25.0 and downloaded_percent < 100.0:
            return

        self.last_download_percents[task.src_path] = downloaded_percent

        progress_str = get_progress_str(task)

        print(progress_str + ": received %6.2f%%" % downloaded_percent)

    def on_uploaded_changed(self, event):
        task = event["emitter"]

        try:
            uploaded_percent = float(task.uploaded) / task.upload_size * 100.0
        except ZeroDivisionError:
            uploaded_percent = 100.0

        last_percent = self.last_upload_percents.get(task.src_path, 0.0)

        # Change can be negative due to retries
        if abs(uploaded_percent - last_percent) < 25.0 and uploaded_percent < 100.0:
            return

        self.last_upload_percents[task.src_path] = uploaded_percent

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

    storage_names = {i.src_storage_name for i in targets}
    storage_names |= {i.dst_storage_name for i in targets}

    ret = authenticate_storages(env, storage_names)

    if ret:
        return ret

    with GenericSignalManager(downloader):
        downloader.start()
        downloader.join()

        if any(i.status not in ("finished", "skipped") for i in targets):
            return 1

        if downloader.stopped:
            return 1

    return 0
