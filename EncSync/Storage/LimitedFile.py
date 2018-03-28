# -*- coding: utf-8 -*-

from .Exceptions import ControllerInterrupt
from .ControlledSpeedLimiter import ControlledSpeedLimiter

__all__ = ["LimitedFile"]

class LimitedFile(object):
    def __init__(self, file, controller, limit=float("inf")):
        self.file = file
        self.limit = limit

        if self.limit != float("inf"):
            self.limit = int(self.limit)

        self.last_delay = 0
        self.cur_read = 0
        self.controller = controller
        self.speed_limiter = ControlledSpeedLimiter(controller, self.limit)

    def __iter__(self):
        return self

    def __next__(self):
        return self.readline()

    def seek(self, *args, **kwargs):
        self.file.seek(*args, **kwargs)

    def tell(self):
        return self.file.tell()

    def delay(self):
        self.speed_limiter.delay()

    def readline(self):
        if self.controller.stopped:
            raise ControllerInterrupt

        self.delay()

        if self.controller.stopped:
            raise ControllerInterrupt

        line = self.file.readline()

        if self.controller.stopped:
            raise ControllerInterrupt

        self.speed_limiter.quantity += len(line)
        self.controller.uploaded = self.file.tell()

        return line

    def read(self, size=-1):
        amount_read = 0

        content = b""

        self.controller.uploaded = self.file.tell()
        
        if self.controller.stopped:
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

            if self.controller.stopped:
                raise ControllerInterrupt

            if size != -1:
                amount_to_read = min(size - amount_read, amount_to_read)

            cur_content = self.file.read(int(amount_to_read))

            if self.controller.stopped:
                raise ControllerInterrupt

            content += cur_content

            l = len(cur_content)

            self.speed_limiter.quantity += l
            amount_read += l

            self.controller.uploaded = self.file.tell()

            if l < amount_to_read:
                break

        return content
