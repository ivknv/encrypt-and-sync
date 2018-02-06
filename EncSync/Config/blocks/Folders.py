#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from ...EncScript.Exceptions import EvaluationError
from ...EncScript.Namespace import Namespace
from ...EncScript import Command
from ...Storage import get_storage
from ...common import recognize_path
from ... import Paths

from ..ConfigBlock import ConfigBlock

__all__ = ["FoldersBlock"]

KNOWN_FILENAME_ENCODINGS = {"base64", "base41"}

def prepare_local_path(path):
    return Paths.dir_normalize(Paths.from_sys(os.path.abspath(os.path.expanduser(path))))

def prepare_remote_path(path):
    return Paths.dir_normalize(Paths.join_properly("/", path))

class FoldersBlock(ConfigBlock):
    def __init__(self, args, body, parent_namespace=None):
        ConfigBlock.__init__(self, args, body, parent_namespace)

        self.namespace = FoldersNamespace(parent_namespace)

    def begin(self, config, *args, **kwargs):
        if len(self.args) > 1:
            raise EvaluationError(self, "Expected no arguments")

    def end(self, config, *args, **kwargs):
        pass

class FoldersNamespace(Namespace):
    def __getitem__(self, key):
        return FolderBlock

class FolderBlock(ConfigBlock):
    def __init__(self, args, body, parent_namespace=None):
        ConfigBlock.__init__(self, args, body, parent_namespace)

        self.folder = None

        self.namespace["encrypted"] = EncryptedCommand
        self.namespace["avoid-rescan"] = AvoidRescanCommand
        self.namespace["filename-encoding"] = FilenameEncodingCommand

    def begin(self, config, *args, **kwargs):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 2 arguments")

        name, path = self.args

        path, path_type = recognize_path(path)

        if path_type == "local":
            path = prepare_local_path(path)
            avoid_rescan = False
        else:
            path = prepare_remote_path(path)
            avoid_rescan = True

        storage_class = get_storage(path_type)

        if storage_class.case_sensitive:
            filename_encoding = "base64"
        else:
            filename_encoding = "base41"

        verbose_name = name + ":" + path_type

        config.folders.setdefault(verbose_name,
                                  {"name":              verbose_name,
                                   "path":              None,
                                   "type":              path_type,
                                   "avoid_rescan":      avoid_rescan,
                                   "encrypted":         False,
                                   "filename_encoding": filename_encoding})
        config.folders[verbose_name]["path"] = path
        self.folder = config.folders[verbose_name]

    def evaluate_body(self, config, *args, **kwargs):
        for i in self.body:
            self.retcode = i.evaluate(config, self.folder, *args, **kwargs)

    def end(self, config, *args, **kwargs):
        pass

class EncryptedCommand(Command):
    def evaluate(self, config, folder, *args, **kwargs):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        arg = self.args[1].lower()

        if arg == "true":
            folder["encrypted"] = True
        elif arg == "false":
            folder["encrypted"] = False
        else:
            msg = "Invalid argument %r, must be 'true' or 'false'" % (arg,)
            raise EvaluationError(self, msg)

class AvoidRescanCommand(Command):
    def evaluate(self, config, folder, *args, **kwargs):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        arg = self.args[1].lower()

        if arg == "true":
            folder["avoid_rescan"] = True
        elif arg == "false":
            folder["avoid_rescan"] = False
        else:
            msg = "Invalid argument %r, must be 'true' or 'false'" % (arg,)
            raise EvaluationError(self, msg)

class FilenameEncodingCommand(Command):
    def evaluate(self, config, folder, *args, **kwargs):
        if len(self.args) != 2:
            raise EvaluationError(self, "Expected 1 argument")

        arg = self.args[1]

        if arg not in KNOWN_FILENAME_ENCODINGS:
            raise EvaluationError(self, "Unknown filename encoding %r" % (arg,))

        folder["filename_encoding"] = arg
