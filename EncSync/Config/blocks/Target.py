# -*- coding: utf-8 -*-

import os

from ... import Paths
from ...common import validate_target_name, recognize_path
from ...EncScript import Command
from ...EncScript.Exceptions import EvaluationError

from ..ConfigBlock import ConfigBlock

__all__ = ["TargetBlock"]

KNOWN_FILENAME_ENCODINGS = ("base64", "base41")

def prepare_local_path(path):
    return Paths.from_sys(os.path.abspath(os.path.expanduser(path)))

def prepare_remote_path(path):
    return Paths.dir_normalize(Paths.join_properly("/", path))

class TargetBlock(ConfigBlock):
    def __init__(self, args, body, parent_namespace=None):
        ConfigBlock.__init__(self, args, body, parent_namespace)
        self.namespace = TargetNamespace(parent_namespace)
        self.target = {"name": None,
                       "src": {},
                       "dst": {},
                       "filename_encoding": "base64",
                       "allowed_paths": {}}

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
        if not self.target["src"]:
            raise EvaluationError(self, "Target has no source")

        if not self.target["dst"]:
            raise EvaluationError(self, "Target has no destination")

        config.targets[self.target["name"]] = self.target

class TargetNamespace(object):
    def __init__(self, parent=None):
        pass

    def __getitem__(self, key):
        if key == "encrypted":
            return EncryptedCommand
        elif key in ("src", "dst"):
            return DirCommand

        raise KeyError("Unknown command/block: %r" % (key,))

class DirCommand(Command):
    def evaluate(self, config, target, *args, **kwargs):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        dir_type, path = self.args

        path, path_type = recognize_path(path)

        if path_type == "local":
            path = prepare_local_path(path)
        else:
            path = prepare_remote_path(path)

        directory = {"name": path_type,
                     "path": path,
                     "encrypted": False,
                     "filename_encoding": "base64"}
        
        target[dir_type] = directory

class EncryptedCommand(Command):
    def evaluate(self, config, target, *args, **kwargs):
        if len(self.args) < 2:
            raise EvaluationError(self, "Expected at least 1 argument")

        for arg in self.args[1:]:
            if ":" in arg:
                dir_type, encoding = arg.rsplit(":", 1)
            else:
                dir_type, encoding = arg, "base64"

            if dir_type not in ("src", "dst"):
                msg = "Wrong directory type: %r, must be 'src' or 'dst'" % (dir_type,)
                raise EvaluationError(self, msg)

            if encoding not in KNOWN_FILENAME_ENCODINGS:
                raise EvaluationError(self, "Unknown filename encoding: %r" % (encoding,))

            target[dir_type]["encrypted"] = True
            target[dir_type]["filename_encoding"] = encoding
