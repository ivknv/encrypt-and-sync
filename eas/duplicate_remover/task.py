# -*- coding: utf-8 -*-

from ..task import Task

__all__ = ["DuplicateRemoverTask"]

class DuplicateRemoverTask(Task):
    def __init__(self, target):
        self._stopped = False

        Task.__init__(self)

        self.parent = target
        self.config = target.config
        self.path = None
        self.ivs = None
        self.prefix = None
        self.filename_encoding = None
        self.storage = None
        self.duplist = target.shared_duplist

    @property
    def stopped(self):
        if self._stopped or self.parent.stopped:
            return True

        return self.status not in (None, "pending")

    @stopped.setter
    def stopped(self, value):
        self._stopped = value

    def autocommit(self):
        self.parent.autocommit()

    def complete(self):
        if self.stopped:
            return True

        self.status = "pending"

        encoding = self.filename_encoding
        encpath = self.config.encrypt_path(self.path, self.prefix,
                                            IVs=self.ivs,
                                            filename_encoding=encoding)[0]

        try:
            self.storage.remove(encpath)
        except FileNotFoundError:
            pass

        self.duplist.remove(self.ivs, self.path)
        self.autocommit()

        self.status = "finished"
