#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from ... import Paths

from ...EncScript import Block, Command

def prepare_local_path(path):
    return Paths.sys_explicit(os.path.realpath(os.path.expanduser(path)))

def prepare_remote_path(path):
    return Paths.dir_normalize(Paths.join_properly("/", path))

class AddTargetCommand(Command):
    def evaluate(self, config):
        if len(self.args) not in (2, 3):
            raise ValueError("Expected 2 or 3 arguments")

        if len(self.args) == 2:
            local, remote = self.args
            name = None
        else:
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

class TargetsBlock(Block):
    def __init__(self, args, body, parent_namespace=None):
        Block.__init__(self, args, body, parent_namespace)
        self.namespace = TargetsNamespace(parent_namespace)

    def begin(self, *args, **kwargs):
        if len(self.args) > 1:
            raise ValueError("Expected no arguments")

    def end(self, *args, **kwargs): pass
