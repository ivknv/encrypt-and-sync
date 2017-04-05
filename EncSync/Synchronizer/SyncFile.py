#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

BLOCK_SIZE = 8192

class SyncFileInterrupt(BaseException):
    pass

class SyncFile(object):
    def __init__(self, file, speed_limit, stop_condition):
        self.file = file
        self.limit = speed_limit
        self.last_delay = 0
        self.cur_read = 0
        self.stop_condition = stop_condition

    def __iter__(self):
        return self

    def __next__(self):
        content = self.read(BLOCK_SIZE)

        if not content:
            raise StopIteration

        return content

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

        if self.stop_condition():
            raise SyncFileInterrupt

        if size == -1:
            amount_to_read = self.limit
            condition = lambda: cur_content
        else:
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

            if l < amount_to_read:
                break

        return content
