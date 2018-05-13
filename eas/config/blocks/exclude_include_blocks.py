#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...encscript import Command
from ...encscript.exceptions import EvaluationError
from ...common import recognize_path
from ..config_block import ConfigBlock

__all__ = ["ExcludeBlock", "IncludeBlock"]

class AddPatternCommand(Command):
    def evaluate(self, config, table):
        if len(self.args) != 1:
            raise EvaluationError(self, "Expected only 1 pattern")

        path, path_type = recognize_path(self.args[0])

        table.setdefault(path_type, [])
        table[path_type].append(path)

class ExcludeNamespace(dict):
    def __init__(self, parent=None):
        dict.__init__(self)

        self.parent = parent

    def __getitem__(self, key):
        return AddPatternCommand

    def get(self, key, default=None):
        return self[key]

class ExcludeBlock(ConfigBlock):
    def __init__(self, args, body, parent_namespace=None):
        ConfigBlock.__init__(self, args, body, parent_namespace)

        self.namespace = ExcludeNamespace(parent_namespace)

        self.exclude_table = {}

    def begin(self, config):
        if len(self.args) > 1:
            raise EvaluationError(self, "Expected 0 arguments")

    def evaluate_body(self, config):
        ConfigBlock.evaluate_body(self, config, self.exclude_table)

    def end(self, config):
        for path_type, patterns in self.exclude_table.items():
            config.allowed_paths.setdefault(path_type, [])
            config.allowed_paths[path_type].append(["e", patterns])

class IncludeBlock(ConfigBlock):
    def __init__(self, args, body, parent_namespace=None):
        ConfigBlock.__init__(self, args, body, parent_namespace)

        self.namespace = ExcludeNamespace(parent_namespace)

        self.include_table = {}

    def begin(self, config):
        if len(self.args) > 2:
            raise EvaluationError(self, "Expected 0 arguments")

    def evaluate_body(self, config):
        ConfigBlock.evaluate_body(self, config, self.include_table)

    def end(self, config):
        for path_type, patterns in self.include_table.items():
            config.allowed_paths.setdefault(path_type, [])
            config.allowed_paths[path_type].append(["i", patterns])

