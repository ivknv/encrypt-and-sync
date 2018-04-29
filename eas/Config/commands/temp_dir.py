# -*- coding: utf-8 -*-

from ...EncScript import Command
from ...EncScript.Exceptions import EvaluationError

__all__ = ["TempDirCommand"]

class TempDirCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        config.temp_dir = self.args[1]
