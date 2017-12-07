# -*- coding: utf-8 -*-

import os

from ... import Paths
from ...common import validate_target_name
from ...EncScript import Command
from ...EncScript.Exceptions import EvaluationError

from ..ConfigBlock import ConfigBlock

__all__ = ["TargetBlock"]

KNOWN_FILENAME_ENCODINGS = ("base64", "base41")

def prepare_local_path(path):
    return Paths.sys_explicit(os.path.realpath(os.path.expanduser(path)))

def prepare_remote_path(path):
    return Paths.dir_normalize(Paths.join_properly("/", path))

class TargetBlock(ConfigBlock):
    def __init__(self, args, body, parent_namespace=None):
        ConfigBlock.__init__(self, args, body, parent_namespace)
        self.namespace = TargetNamespace(parent_namespace)
        self.target = {"name": None,
                       "dirs": {"local": None,
                                "remote": None}
                       "filename_encoding": "base64",
                       "allowed_paths": []}

    def begin(self, config, *args, **kwargs):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        name = self.args[1]

        if not validate_target_name(name):
            raise EvaluationError(self, "Invalid target name: %r" % (name,))

        self.target["name"] = name

    def evaluate_body(self, config, *args, **kwargs):
        for i in self.body:
            self.retcode = i.evaluate(config, self.target, *args, **kwargs)

    def end(self, config, *args, **kwargs):
        if self.target["dirs"]["local"] is None:
            raise EvaluationError(self, "Target is missing the local path")

        if self.target["dirs"]["remote"] is None:
            raise EvaluationError(self, "Target is missing the remote path")

        config.targets[self.target["name"]] = self.target

class TargetNamespace(dict):
    def __init__(self, parent=None):
        dict.__init__(self)

        self["local"] = LocalCommand
        self["remote"] = RemoteCommand
        self["filename-encoding"] = FilenameEncodingCommand

class LocalCommand(Command):
    def evaluate(self, config, target, *args, **kwargs):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        target["dirs"]["local"] = prepare_local_path(self.args[1])

class RemoteCommand(Command):
    def evaluate(self, config, target, *args, **kwargs):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        target["dirs"]["remote"] = prepare_remote_path(self.args[1])

class FilenameEncodingCommand(Command):
    def evaluate(self, config, target, *args, **kwargs):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        encoding = self.args[1]

        if encoding not in KNOWN_FILENAME_ENCODINGS:
            raise EvaluationError(self, "Unknown filename encoding: %r" % (encoding,))
        
        target["filename_encoding"] = encoding
