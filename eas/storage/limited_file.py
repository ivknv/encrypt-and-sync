# -*- coding: utf-8 -*-

import weakref

from .exceptions import ControllerInterrupt
from .stoppable_speed_limiter import StoppableSpeedLimiter

__all__ = ["LimitedFile"]

class LimitedFile(object):
    def __init__(self, file, upload_task, limit=None):
        self.file = file
        self.weak_task = weakref.ref(upload_task)

        if limit is None:
            limit = float("inf")

        if limit != float("inf"):
            limit = int(limit)

        self.last_delay = 0
        self.cur_read = 0
        self.speed_limiter = StoppableSpeedLimiter(limit, interval=0.5)
        self.stopped = False

    @property
    def limit(self):
        return self.speed_limiter.limit

    @limit.setter
    def limit(self, value):
        self.speed_limiter.limit = value

    def stop(self):
        self.stopped = True
        self.speed_limiter.stop()

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()

        if not line:
            raise StopIteration

        return line

    def seek(self, *args, **kwargs):
        return self.file.seek(*args, **kwargs)

    def tell(self):
        return self.file.tell()

    def delay(self):
        self.speed_limiter.delay()

    def readline(self):
        task = self.weak_task()

        if self.stopped:
            raise ControllerInterrupt

        self.delay()

        if self.stopped:
            raise ControllerInterrupt

        line = self.file.readline()

        if self.stopped:
            raise ControllerInterrupt

        self.speed_limiter.quantity += len(line)

        return line

    def read(self, size=-1):
        task = self.weak_task()

        amount_read = 0

        content = b""

        task.uploaded = self.file.tell()
        
        if self.stopped:
            raise ControllerInterrupt

        if size == -1:
            amount_to_read = self.limit
            if amount_to_read == float("inf"):
                amount_to_read = -1
            condition = lambda: cur_content
            # Just any non-empty string
            cur_content = b"1"
        else:
            amount_to_read = min(self.limit, size)
            condition = lambda: amount_read < size

        while condition():
            self.delay()

            if self.stopped:
                raise ControllerInterrupt

            if size != -1:
                amount_to_read = min(size - amount_read, amount_to_read)

            cur_content = self.file.read(int(amount_to_read))

            if self.stopped:
                raise ControllerInterrupt

            content += cur_content

            l = len(cur_content)

            self.speed_limiter.quantity += l
            amount_read += l

            task.uploaded = self.file.tell()

            if l < amount_to_read:
                break

        return content
