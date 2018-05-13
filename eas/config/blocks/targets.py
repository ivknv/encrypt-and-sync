#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...encscript.exceptions import EvaluationError
from ...encscript.namespace import Namespace
from ...encscript import Command
from ...common import validate_folder_name

from ..config_block import ConfigBlock

__all__ = ["TargetsBlock"]

class TargetsBlock(ConfigBlock):
    def __init__(self, args, body, parent_namespace=None):
        ConfigBlock.__init__(self, args, body, parent_namespace)

        self.namespace = TargetsNamespace(parent_namespace)

    def begin(self, config, *args, **kwargs):
        if len(self.args) != 1:
            raise EvaluationError(self, "Expected no arguments")

    def end(self, config, *args, **kwargs):
        pass

class TargetsNamespace(Namespace):
    def __getitem__(self, key):
        return TargetCommand

class TargetCommand(Command):
    def evaluate(self, config, *args, **kwargs):
        if len(self.args) == 3:
            folder1, arrow, folder2 = self.args

            if arrow in ("<-", "<="):
                folder1, folder2 = folder2, folder1
            elif arrow not in ("->", "=>"):
                raise EvaluationError(self, "Bad arrow: %r instead of '->' or '=>'" % (arrow,))
        elif len(self.args) == 2:
            folder1, folder2 = self.args
        else:
            raise EvaluationError(self, "Expected 2 or 3 arguments")

        for i in (folder1, folder2):
            if not validate_folder_name(i):
                raise EvaluationError(self, "Invalid folder name: %r" % (i,))

            if i not in config.folders:
                raise EvaluationError(self, "Unknown folder name: %r" % (i,))

        config.sync_targets.append((folder1, folder2))
