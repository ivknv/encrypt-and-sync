#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

MIN_READ_SIZE = 512 * 1024 # Bytes

class SyncFileInterrupt(BaseException):
    pass

class SyncFile(object):
    def __init__(self, file, worker, task):
        self.file = file
        self.limit = worker.speed_limit

        if self.limit != float("inf"):
            self.limit = int(self.limit)

        self.last_delay = 0
        self.cur_read = 0
        self.stop_condition = worker.stop_condition
        self.task = task

    def seek(self, *args, **kwargs):
        self.file.seek(*args, **kwargs)

    def tell(self):
        return self.file.tell()

    def delay(self):
        if self.cur_read > self.limit:
            ratio = float(self.cur_read) / float(self.limit)
            sleep_duration = (1.0 * ratio) - (time.time() - self.last_delay)

            if sleep_duration > 0.0:
                time.sleep(sleep_duration)

            self.cur_read = 0
            self.last_delay = time.time()

    def read(self, size=-1):
        amount_read = 0

        content = b""

        self.task.uploaded = self.file.tell()

        if self.stop_condition():
            raise SyncFileInterrupt

        if size == -1:
            amount_to_read = self.limit
            condition = lambda: cur_content
        else:
            size = max(MIN_READ_SIZE, size)
            amount_to_read = min(self.limit, size)
            condition = lambda: amount_read < size

        while condition():
            self.delay()

            if size != -1:
                amount_to_read = min(size - amount_read, amount_to_read)

            cur_content = self.file.read(amount_to_read)

            content += cur_content

            l = len(cur_content)

            self.cur_read += l
            amount_read += l

            self.task.uploaded = self.file.tell()

            if l < amount_to_read:
                break

        return content
