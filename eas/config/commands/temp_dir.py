# -*- coding: utf-8 -*-

from ...encscript import Command
from ...encscript.exceptions import EvaluationError

__all__ = ["TempDirCommand"]

class TempDirCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        config.temp_dir = self.args[1]
