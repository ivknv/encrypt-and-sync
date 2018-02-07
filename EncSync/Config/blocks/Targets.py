#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...EncScript.Exceptions import EvaluationError
from ...EncScript.Namespace import Namespace
from ...EncScript import Command

from ..ConfigBlock import ConfigBlock

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

        config.sync_targets.append((folder1, folder2))
