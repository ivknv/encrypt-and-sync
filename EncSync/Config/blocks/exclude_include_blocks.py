#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from ... import Paths

from ...EncScript import Command
from ...EncScript.Exceptions import EvaluationError
from ...common import recognize_path
from ..ConfigBlock import ConfigBlock

__all__ = ["ExcludeBlock", "IncludeBlock"]

def prepare_local_path(path):
    return Paths.from_sys(os.path.expanduser(path))

def prepare_remote_path(path):
    return Paths.join_properly("/", path)

class AddExcludeCommand(Command):
    def evaluate(self, config, exclude_table):
        if len(self.args) != 1:
            raise EvaluationError(self, "Expected only 1 pattern")

        path, path_type = recognize_path(self.args[0])

        if path_type == "local":
            path = prepare_local_path(path)
        else:
            path = prepare_remote_path(path)

        exclude_table.setdefault(path_type, [])
        exclude_table[path_type].append(path)

class AddIncludeCommand(Command):
    def evaluate(self, config, include_table):
        if len(self.args) != 1:
            raise EvaluationError(self, "Expected only 1 pattern")

        path, path_type = recognize_path(self.args[0])

        if path_type == "local":
            path = prepare_local_path(path)
        else:
            path = prepare_remote_path(path)

        include_table.setdefault(path_type, [])
        include_table[path_type].append(path)

class ExcludeNamespace(dict):
    def __init__(self, parent=None):
        dict.__init__(self)

        self.parent = parent

    def __getitem__(self, key):
        return AddExcludeCommand

    def get(self, key, default=None):
        return self[key]

class IncludeNamespace(dict):
    def __init__(self, parent=None):
        dict.__init__(self)

        self.parent = parent

    def __getitem__(self, key):
        return AddIncludeCommand

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

        self.namespace = IncludeNamespace(parent_namespace)

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

