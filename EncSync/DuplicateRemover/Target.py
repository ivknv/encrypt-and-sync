# -*- coding: utf-8 -*-

from ..Task import Task

__all__ = ["DuplicateRemoverTarget"]

class DuplicateRemoverTarget(Task):
    def __init__(self):
        Task.__init__(self)

        self.path = None
        self.prefix = None
        self.storage = None
        self.filename_encoding = None

        self.total_children = 0
