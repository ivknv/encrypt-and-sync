#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from ... import Paths

from ..Block import Block
from ..Command import Command

def prepare_path(path):
    return Paths.from_sys(path)

class AddExcludeCommand(Command):
    def evaluate(self, config, exclude_list):
        if len(self.args) != 1:
            raise ValueError("Expected only 1 pattern")

        exclude_list.append(prepare_path(self.args[0]))

class AddIncludeCommand(Command):
    def evaluate(self, config, include_list):
        if len(self.args) != 1:
            raise ValueError("Expected only 1 pattern")

        include_list.append(prepare_path(self.args[0]))

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

class ExcludeBlock(Block):
    def __init__(self, args, body, parent_namespace=None):
        Block.__init__(self, args, body, parent_namespace)

        self.namespace = ExcludeNamespace(parent_namespace)

        self.exclude_list = []

    def begin(self, config):
        if len(self.args) > 1:
            raise ValueError("Expected no arguments")

        config.allowed_paths.append(["e", self.exclude_list])

    def evaluate_body(self, config):
        Block.evaluate_body(self, config, self.exclude_list)

    def end(self, config): pass

class IncludeBlock(Block):
    def __init__(self, args, body, parent_namespace=None):
        Block.__init__(self, args, body, parent_namespace)

        self.namespace = IncludeNamespace(parent_namespace)

        self.include_list = []

    def begin(self, config):
        if len(self.args) > 1:
            raise ValueError("Expected no arguments")

        config.allowed_paths.append(["i", self.include_list])

    def end(self, config): pass
