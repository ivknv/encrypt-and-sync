# -*- coding: utf-8 -*-

import yadisk.settings

from ...EncScript import Command
from ...EncScript.Exceptions import EvaluationError

__all__ = ["ConnectTimeoutCommand", "ReadTimeoutCommand",
           "UploadConnectTimeoutCommand", "UploadReadTimeoutCommand"]

class ConnectTimeoutCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        try:
            connect_timeout = float(self.args[1])

            # Catches NaN too
            if not connect_timeout > 0.0:
                raise ValueError
        except ValueError:
            raise EvaluationError(self, "Timeout must be a positive number")

        if connect_timeout == float("inf"):
            connect_timeout = None

        if not isinstance(yadisk.settings.DEFAULT_TIMEOUT, (tuple, list)):
            read_timeout = yadisk.settings.DEFAULT_TIMEOUT
        else:
            read_timeout = yadisk.settings.DEFAULT_TIMEOUT[1]

        yadisk.settings.DEFAULT_TIMEOUT = (connect_timeout, read_timeout)

        return 0

class ReadTimeoutCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        try:
            read_timeout = float(self.args[1])

            # Catches NaN too
            if not read_timeout > 0.0:
                raise ValueError
        except ValueError:
            raise EvaluationError(self, "Timeout must be a positive number")

        if read_timeout == float("inf"):
            read_timeout = None

        if not isinstance(yadisk.settings.DEFAULT_TIMEOUT, (tuple, list)):
            connect_timeout = yadisk.settings.DEFAULT_TIMEOUT
        else:
            connect_timeout = yadisk.settings.DEFAULT_TIMEOUT[0]

        yadisk.settings.DEFAULT_TIMEOUT = (connect_timeout, read_timeout)

        return 0

class UploadConnectTimeoutCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        try:
            connect_timeout = float(self.args[1])

            # Catches NaN too
            if not connect_timeout > 0.0:
                raise ValueError
        except ValueError:
            raise EvaluationError(self, "Timeout must be a positive number")

        if connect_timeout == float("inf"):
            connect_timeout = None

        if not isinstance(yadisk.settings.DEFAULT_UPLOAD_TIMEOUT, (tuple, list)):
            read_timeout = yadisk.settings.DEFAULT_UPLOAD_TIMEOUT
        else:
            read_timeout = yadisk.settings.DEFAULT_UPLOAD_TIMEOUT[1]

        yadisk.settings.DEFAULT_UPLOAD_TIMEOUT = (connect_timeout, read_timeout)

        return 0

class UploadReadTimeoutCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        try:
            read_timeout = float(self.args[1])

            # Catches NaN too
            if not read_timeout > 0.0:
                raise ValueError
        except ValueError:
            raise EvaluationError(self, "Timeout must be a positive number")

        if read_timeout == float("inf"):
            read_timeout = None

        if not isinstance(yadisk.settings.UPLOAD_DEFAULT_TIMEOUT, (tuple, list)):
            connect_timeout = yadisk.settings.DEFAULT_UPLOAD_TIMEOUT
        else:
            connect_timeout = yadisk.settings.DEFAULT_UPLOAD_TIMEOUT[0]

        yadisk.settings.DEFAULT_UPLOAD_TIMEOUT = (connect_timeout, read_timeout)

        return 0
