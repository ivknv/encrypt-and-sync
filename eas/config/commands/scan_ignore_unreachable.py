# -*- coding: utf-8 -*-

from ...encscript import Command
from ...encscript.exceptions import EvaluationError

__all__ = ["ScanIgnoreUnreachableCommand"]

class ScanIgnoreUnreachableCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        ignore = self.args[1].lower()

        if ignore == "true":
            config.ignore_unreachable = True
        elif ignore == "false":
            config.ignore_unreachable = False
        else:
            raise EvaluationError(self, "Expected either 'true' or 'false'")

        return 0
