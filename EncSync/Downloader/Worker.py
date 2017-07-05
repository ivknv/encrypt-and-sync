#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import time

from ..Encryption import MIN_ENC_SIZE
from ..Worker import Worker
from .. import Paths
from .Logging import logger
from ..Scannable import LocalScannable
from .Exceptions import FailedToObtainLinkError

def check_if_download(task):
    if not os.path.exists(task.local):
        return True

    s = LocalScannable(task.local)
    s.identify()

    return s.size + MIN_ENC_SIZE != task.size or s.modified < task.modified

def recursive_mkdir(path, basedir="."):
    if not path:
        return

    path = os.path.relpath(path, basedir)

    p = basedir

    for i in path.split(os.path.sep):
        if not i:
            continue
        p = os.path.join(p, i)

        try:
            os.mkdir(p)
        except FileExistsError:
            pass

class DownloaderWorker(Worker):
    def __init__(self, dispatcher, target):
        Worker.__init__(self, dispatcher)
        self.target = target
        self.pool = self.target.pool
        self.encsync = dispatcher.encsync
        self.lock = self.target.pool_lock
        self.speed_limit = dispatcher.speed_limit
        self.cur_task = None

        self.add_event("next_task")

    def get_info(self):
        if self.cur_task is not None:
            try:
                progress = float(self.cur_task.downloaded) / self.cur_task.size
            except ZeroDivisionError:
                progress = 1.0

            return {"operation": "downloading",
                    "path":      self.cur_task.dec_remote,
                    "progress":  progress}

        return {"operation": "downloading",
                "progress":  0.0}

    def download_file(self, task):
        try:
            if os.path.isdir(task.local):
                name = Paths.split(task.dec_remote)[1]
                task.local = os.path.join(task.local, name)

            if not check_if_download(task):
                task.change_status("finished")
                return

            recursive_mkdir(os.path.split(task.local)[0])

            link = task.obtain_link(self.encsync.ynd)

            if link is None:
                raise FailedToObtainLinkError("Failed to obtain download link to %r" % task.dec_remote, task.dec_remote)

            task.link = link

            with tempfile.TemporaryFile(mode="w+b") as tmpfile:
                r = self.encsync.ynd.make_session().get(task.link, stream=True)

                cur_downloaded = 0
                t1 = time.time()

                for chunk in r.iter_content(chunk_size=4096):
                    if self.stopped or self.target.status == "suspended":
                        return

                    if not len(chunk):
                        continue

                    tmpfile.write(chunk)
                    task.downloaded += len(chunk)

                    cur_downloaded += len(chunk)

                    if cur_downloaded > self.speed_limit:
                        t2 = time.time()

                        ratio = float(cur_downloaded) / self.speed_limit

                        sleep_duration = (1.0 * ratio) - (t2 - t1)

                        if sleep_duration > 0.0:
                            time.sleep(sleep_duration)
                        t1 = time.time()
                        cur_downloaded = 0

                tmpfile.flush()
                tmpfile.seek(0)
                self.encsync.decrypt_file(tmpfile, task.local)
            task.change_status("finished")
        except Exception as e:
            self.emit_event("error", e)
            task.change_status("failed")

    def work(self):
        while not self.stopped:
            try:
                with self.lock:
                    if self.stopped or not len(self.pool):
                        break

                    task = self.pool.pop(0)
                    self.cur_task = task

                    self.emit_event("next_task", task)

                    if task.parent is not None and task.parent.status == "suspended":
                        continue

                    if task.status is None:
                        task.change_status("pending")
                    elif task.status != "pending":
                        continue

                if task.type == "d":
                    recursive_mkdir(task.local)
                    task.change_status("finished")
                    continue

                self.download_file(task)

                self.cur_task = None
            except Exception as e:
                self.emit_event("error", e)

                if self.cur_task is not None:
                    self.cur_task.change_status("failed")
