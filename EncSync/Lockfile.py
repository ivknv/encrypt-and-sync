# -*- coding: utf-8 -*-

import os

import portalocker

__all__ = ["Lockfile"]

class Lockfile(object):
    def __init__(self, path):
        self.lock = None
        self.path = path

        self.lock = portalocker.Lock(path, "w", timeout=1, fail_when_locked=True,
                                     flags=portalocker.LOCK_EX | portalocker.LOCK_NB)
        self.file = None

    def __del__(self):
        if self.file is not None:
            self.release()

    def acquire(self):
        self.file = self.lock.acquire()

    def release(self):
        self.lock.release()
        self.file = None

        try:
            os.remove(self.path)
        except IOError:
            pass
