#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...EncScript import Command
from ...EncScript.Exceptions import EvaluationError

def parse_size(s):
    if s.lower() in ("inf", "nan"):
        return float(s)

    try:
        last = s[-1].lower()

        try:
            if last.isdigit():
                return float(s)
        except ValueError:
            raise ValueError("Expected a non-negative number")
    except IndexError:
        return 0

    powers = {"k": 1, "m": 2, "g": 3}

    try:
        power = powers[last]
    except KeyError:
        raise ValueError("Unknown size suffix: %r" % last)

    try:
        return float(s[:-1]) * 1024 ** power
    except ValueError:
        raise ValueError("Expected a non-negative number")

class UploadLimitCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError("Expected 1 argument")

        try:
            limit = parse_size(self.args[1])
        except ValueError as e:
            raise EvaluationError(self, str(e))

        if not limit >= 0.0:
            raise EvaluationError(self, "Expected a non-negative number")

        config.upload_limit = limit

class DownloadLimitCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        try:
            limit = parse_size(self.args[1])
        except ValueError as e:
            raise EvaluationError(self, str(e))

        if not limit >= 0.0:
            raise EvaluationError(self, "Expected a non-negative number")

        config.download_limit = limit
