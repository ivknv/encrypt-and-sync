# -*- coding: utf-8 -*-

from ...encscript import Command
from ...encscript.exceptions import EvaluationError

__all__ = ["NRetriesCommand"]

class NRetriesCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        try:
            n_retries = int(self.args[1])

            if n_retries < 0:
                raise ValueError
        except ValueError:
            raise EvaluationError(self, "Expected a non-negative integer")

        config.n_retries = n_retries

        return 0
