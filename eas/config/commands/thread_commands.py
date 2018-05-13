#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...encscript import Command
from ...encscript.exceptions import EvaluationError

def is_positive_int(x):
    try:
        if int(x) > 0:
            return True

        return False
    except ValueError:
        return False

class SyncThreadsCommand(Command):
    def evaluate(self, config):
        arg = self.args[1]

        if not is_positive_int(arg):
            raise EvaluationError(self, "Expected a positive integer")

        config.sync_threads = int(arg)

class ScanThreadsCommand(Command):
    def evaluate(self, config):
        arg = self.args[1]

        if not is_positive_int(arg):
            raise EvaluationError(self, "Expected a positive integer")

        config.scan_threads = int(arg)

class DownloadThreadsCommand(Command):
    def evaluate(self, config):
        arg = self.args[1]

        if not is_positive_int(arg):
            raise EvaluationError(self, "Expected a positive integer")

        config.download_threads = int(arg)
