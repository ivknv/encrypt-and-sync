#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...encscript import Command
from ...encscript.exceptions import EvaluationError
from ...common import parse_size

__all__ = ["UploadLimitCommand", "DownloadLimitCommand", "TempEncryptBufferLimitCommand"]

class UploadLimitCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

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

class TempEncryptBufferLimitCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        try:
            limit = parse_size(self.args[1])
        except ValueError as e:
            raise EvaluationError(self, str(e))

        if not limit >= 0.0:
            raise EvaluationError(self, "Expected a non-negative number")

        config.temp_encrypt_buffer_limit = limit
