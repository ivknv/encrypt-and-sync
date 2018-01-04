# -*- coding: utf-8 -*-

from ..Task import Task

__all__ = ["DuplicateRemoverTask"]

class DuplicateRemoverTask(Task):
    def __init__(self):
        Task.__init__(self)

        self.path = None
        self.ivs = None
        self.prefix = None
        self.filename_encoding = None
        self.storage = None
