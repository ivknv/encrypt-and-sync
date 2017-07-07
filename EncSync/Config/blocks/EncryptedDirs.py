#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ... import Paths

from ..Block import Block
from ..Command import Command

def prepare_remote_path(path):
    return Paths.dir_normalize(Paths.join_properly("/", path))

class AddEncryptedDirCommand(Command):
    def evaluate(self, config):
        if len(self.args) != 1:
            raise ValueError("Expected only 1 path")

        config.encrypted_dirs.add(prepare_remote_path(self.args[0]))

class EncryptedDirsNamespace(dict):
    def __init__(self, parent=None):
        dict.__init__(self, parent)

        self.parent = parent

    def __getitem__(self, key):
        return AddEncryptedDirCommand

    def get(self, key, default=None):
        return self[key]

class EncryptedDirsBlock(Block):
    def __init__(self, args, body, parent_namespace=None):
        Block.__init__(self, args, body, parent_namespace)

        self.namespace = EncryptedDirsNamespace(parent_namespace)

    def begin(self, config):
        if len(self.args) > 1:
            raise ValueError("Expected no arguments")

        config.encrypted_dirs.clear()

    def end(self, config): pass
