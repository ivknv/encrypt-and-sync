#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

import portalocker

from .. import pathm
from ..downloader import Downloader, DownloadTarget
from ..events import Receiver
from ..common import Lockfile

from . import common
from .authenticate_storages import authenticate_storages
from .common import get_progress_str, make_size_readable
from .generic_signal_manager import GenericSignalManager

def print_target_totals(target):
    n_finished = target.progress["finished"] + target.progress["skipped"]
    n_failed = target.progress["failed"]
    n_total = target.total_children
    downloaded = make_size_readable(target.downloaded)

    dst_path, src_path = target.dst_path, target.src_path
    dst_path = "%s://%s" % (target.dst_storage_name, dst_path)
    src_path = "%s://%s" % (target.src_storage_name, src_path)

    print("[%s -> %s]: %d tasks in total" % (src_path, dst_path, n_total))
    print("[%s -> %s]: %d tasks successful" % (src_path, dst_path, n_finished))
    print("[%s -> %s]: %d tasks failed" % (src_path, dst_path, n_failed))
    print("[%s -> %s]: %s downloaded" % (src_path, dst_path, downloaded))

class DownloaderReceiver(Receiver):
    def __init__(self, env, downloader):
        Receiver.__init__(self)

        self.downloader = downloader

    def on_next_target(self, event, target):
        src_path = "%s://%s" % (target.src_storage_name, target.src_path)
        dst_path = "%s://%s" % (target.dst_storage_name, target.dst_path)
        print("Next target: [%s -> %s]" % (src_path, dst_path))

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

        self.pool_worker = PoolReceiver(env)

    def on_status_changed(self, event):
        target = event["emitter"]

        status = target.status

        if status != "pending":
            dst_path = "%s://%s" % (target.dst_storage_name, target.dst_path)
            src_path = "%s://%s" % (target.src_storage_name, target.src_path)

            print("[%s -> %s]: %s" % (src_path, dst_path, status))
        else:
            target.pool.add_receiver(self.pool_worker)

        if status in ("finished", "failed",):
            print_target_totals(target)

class WorkerReceiver(Receiver):
    def __init__(self, env):
        Receiver.__init__(self)

        self.env = env
        self.task_receiver = TaskReceiver()

    def on_next_task(self, event, task):
        if self.env.get("no_progress", False):
            return

        progress_str = get_progress_str(task)

        print(progress_str + ": downloading")

        task.add_receiver(self.task_receiver)

    def on_error(self, event, exc):
        common.show_exception(exc)

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
        percent_step_count = max(min(int(task.download_size / 1024.0**2), 100), 1)
        percent_step = 100.0 / percent_step_count

        # Change can be negative due to retries
        if abs(downloaded_percent - last_percent) < percent_step and downloaded_percent < 100.0:
            return

        self.last_download_percents[task.src_path] = downloaded_percent

        progress_str = get_progress_str(task)

        print(progress_str + ": received %6.2f%%" % (downloaded_percent,))

    def on_uploaded_changed(self, event):
        task = event["emitter"]

        try:
            uploaded_percent = float(task.uploaded) / task.upload_size * 100.0
        except ZeroDivisionError:
            uploaded_percent = 100.0

        last_percent = self.last_upload_percents.get(task.src_path, 0.0)
        percent_step_count = max(min(int(task.upload_size / 1024.0**2), 100), 1)
        percent_step = 100.0 / percent_step_count

        # Change can be negative due to retries
        if abs(uploaded_percent - last_percent) < percent_step and uploaded_percent < 100.0:
            return

        self.last_upload_percents[task.src_path] = uploaded_percent

        progress_str = get_progress_str(task)

        print(progress_str + ": sent %6.2f%%" % (uploaded_percent,))

def download(env, paths):
    lockfile = Lockfile(env["lockfile_path"])

    try:
        lockfile.acquire()
    except portalocker.exceptions.AlreadyLocked:
        common.show_error("Error: there can be only one Encrypt & Sync (the lockfile is already locked)")
        return 1

    config, ret = common.make_config(env)

    if config is None:
        return ret

    n_workers = env.get("n_workers", config.download_threads)
    no_skip = env.get("no_skip", False)

    downloader = Downloader(config, env["db_dir"])
    downloader.upload_limit = config.upload_limit
    downloader.download_limit = config.download_limit

    downloader_receiver = DownloaderReceiver(env, downloader)
    downloader.add_receiver(downloader_receiver)

    target_receiver = TargetReceiver(env)

    targets = []

    if len(paths) == 1:
        dst_path = pathm.from_sys(os.getcwd())
    else:
        dst_path = paths.pop()

    dst_path, dst_path_type = common.recognize_path(dst_path)

    if dst_path_type == "local":
        dst_path = pathm.from_sys(os.path.abspath(pathm.to_sys(dst_path)))
    else:
        dst_path = pathm.join_properly("/", dst_path)

    for src_path in paths:
        src_path, src_path_type = common.recognize_path(src_path)

        if src_path_type == "local":
            src_path = pathm.from_sys(os.path.abspath(pathm.to_sys(src_path)))
        else:
            src_path = pathm.join_properly("/", src_path)

        target = DownloadTarget(downloader,
                                src_path_type, src_path,
                                dst_path_type, dst_path)
        target.n_workers = n_workers
        target.skip_downloaded = not no_skip
        target.add_receiver(target_receiver)
        targets.append(target)

        downloader.add_target(target)

    storage_names = {i.src_storage_name for i in targets}
    storage_names |= {i.dst_storage_name for i in targets}

    ret = authenticate_storages(env, storage_names)

    if ret:
        return ret

    with GenericSignalManager(downloader):
        print("Downloader: starting")

        # This contraption is needed to silence a SystemExit traceback
        # The traceback would be printed otherwise due to use of a finally clause
        try:
            try:
                downloader.run()
            finally:
                print("Downloader: finished")
        except SystemExit as e:
            sys.exit(e.code)

    if any(i.status not in ("finished", "skipped") for i in targets):
        return 1

    if downloader.stopped:
        return 1

    return 0
