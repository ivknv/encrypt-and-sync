# -*- coding: utf-8 -*-

import yadisk.settings

from ...EncScript import Command
from ...EncScript.Exceptions import EvaluationError

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

        yadisk.settings.DEFAULT_N_RETRIES = n_retries

        return 0
