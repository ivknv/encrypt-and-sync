#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from ... import Paths

from ...EncScript import Command
from ...EncScript.Exceptions import EvaluationError
from ..ConfigBlock import ConfigBlock

def prepare_local_path(path):
    return Paths.sys_explicit(os.path.realpath(os.path.expanduser(path)))

def prepare_remote_path(path):
    return Paths.dir_normalize(Paths.join_properly("/", path))

class AddTargetCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 3:
            raise EvaluationError(self, "Expected 3 arguments")

        name, local, remote = self.args

        local  = prepare_local_path(local)
        remote = prepare_remote_path(remote)

        config.targets.append({"name":          name,
                               "local":         local,
                               "remote":        remote,
                               "allowed_paths": []})

class TargetsNamespace(dict):
    def __init__(self, parent=None):
        dict.__init__(self)

        self.parent = parent

    def __getitem__(self, key):
        return AddTargetCommand

    def get(self, key, default=None):
        return self[key]

class TargetsBlock(ConfigBlock):
    def __init__(self, args, body, parent_namespace=None):
        ConfigBlock.__init__(self, args, body, parent_namespace)
        self.namespace = TargetsNamespace(parent_namespace)

    def begin(self, *args, **kwargs):
        if len(self.args) > 1:
            raise EvaluationError(self, "Expected no arguments")

    def end(self, *args, **kwargs): pass
