#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import time

from ..Worker import Worker
from .. import Paths
from .Logging import logger

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

    def download_file(self, task, task_copy):
        logger.debug("Downloading file {} to {}".format(task_copy.dec_remote, task_copy.local))

        if os.path.isdir(task.local):
            name = Paths.split(task.dec_remote)[1]
            task.local = os.path.join(task.local, name)
            task_copy.local = task.local

        try:
            if os.path.exists(task_copy.local):
                task.change_status("finished")
                return

            recursive_mkdir(os.path.split(task_copy.local)[0])

            task.obtain_link(self.encsync.ynd)

            with task.lock:
                if task.status == "failed":
                    logger.debug("Failed to obtain download link")
                    return

                task_copy.link = task.link

            with tempfile.TemporaryFile(mode="w+b") as tmpfile:
                r = self.encsync.ynd.make_session().get(task_copy.link, stream=True)

                cur_downloaded = 0
                t1 = time.time()

                for chunk in r.iter_content(chunk_size=4096):
                    if self.stopped or self.target.status == "suspended":
                        return

                    if not len(chunk):
                        continue

                    tmpfile.write(chunk)
                    with task.lock:
                        task.downloaded += len(chunk)
                        if task.parent is not None:
                            with task.parent.lock:
                                task.parent.downloaded += len(chunk)
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
                logger.debug("Decrypting file")
                self.encsync.decrypt_file(tmpfile, task_copy.local)
                logger.debug("Done decrypting file")
            task.change_status("finished")
            logger.debug("Successfully downloaded file")
        except:
            task.change_status("failed")
            logger.exception("An error occured")

    def work(self):
        logger.debug("Worker began working")

        try:
            while not self.stopped:
                with self.lock:
                    if self.stopped or not len(self.pool):
                        break

                    task = self.pool.pop(0)
                    self.cur_task = task

                    if task.parent is not None and task.parent.status == "suspended":
                        continue

                    if task.status is None:
                        task.change_status("pending")
                    elif task.status != "pending":
                        continue

                    task_copy = task.copy()

                logger.debug("Downloading to {}".format(task_copy.local))

                if task_copy.type == "d":
                    recursive_mkdir(task_copy.local)
                    task.change_status("finished")
                    continue

                self.download_file(task, task_copy)
        except:
            logger.exception("An error occured")
        finally:
            logger.debug("Worker finished working")
