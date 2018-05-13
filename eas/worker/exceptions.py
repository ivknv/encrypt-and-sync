#!/usr/bin/env python
# -*- coding: utf-8 -*-

class WorkerError(Exception):
    pass

class DuplicateStageError(WorkerError):
    def __init__(self, name):
        self.name = name

        msg = "Stage %r already exists" % name

        WorkerError.__init__(self, msg)

class UnknownStageError(WorkerError):
    def __init__(self, name):
        self.name = name

        msg = "Unknown stage %r" % name

        WorkerError.__init__(self, msg)
