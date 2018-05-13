# -*- coding: utf-8 -*-

from ..task import Task

__all__ = ["DuplicateRemoverTask"]

class DuplicateRemoverTask(Task):
    def __init__(self, target):
        Task.__init__(self)

        self.parent = target
        self.config = target.config
        self.path = None
        self.ivs = None
        self.prefix = None
        self.filename_encoding = None
        self.storage = None
        self.duplist = target.shared_duplist

    def stop_condition(self, worker):
        if worker.stopped:
            return True

        if self.parent.stop_condition():
            return True

        return self.status not in (None, "pending")

    def autocommit(self):
        self.parent.autocommit()

    def complete(self, worker):
        if self.stop_condition(worker):
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
