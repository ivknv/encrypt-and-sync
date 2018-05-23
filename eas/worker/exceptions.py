# -*- coding: utf-8 -*-

__all__ = ["WorkerError", "DuplicateStageError", "UnknownStageError"]

class WorkerError(Exception):
    pass

class DuplicateStageError(WorkerError):
    def __init__(self, name):
        self.name = name

        msg = "Stage %r already exists" % name

        WorkerError.__init__(self, msg)

class UnknownStageError(WorkerError, KeyError):
    def __init__(self, name):
        self.name = name

        msg = "Unknown stage %r" % name

        WorkerError.__init__(self, msg)
