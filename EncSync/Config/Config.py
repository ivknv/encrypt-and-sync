#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..EncScript import Parser, Tokenizer, Namespace, Program, ast2program
from .Exceptions import InvalidConfigError

from . import commands, blocks

class ConfigNamespace(Namespace):
    def __init__(self):
        Namespace.__init__(self)

        self["sync-threads"] = commands.SyncThreadsCommand
        self["scan-threads"] = commands.ScanThreadsCommand
        self["upload-limit"] = commands.UploadLimitCommand
        self["download-limit"] = commands.DownloadLimitCommand
        self["download-threads"] = commands.DownloadThreadsCommand

        self["targets"] = blocks.TargetsBlock
        self["include"] = blocks.IncludeBlock
        self["exclude"] = blocks.ExcludeBlock
        self["encrypted-dirs"] = blocks.EncryptedDirsBlock

class ConfigProgram(Program):
    def __init__(self, body):
        Program.__init__(self, body)

        self.namespace = ConfigNamespace()

    def evaluate(self, config):
        Program.evaluate(self, config)

class Config(object):
    def __init__(self):
        self.sync_threads = 1
        self.scan_threads = 1
        self.download_threads = 1
        self.upload_limit = float("inf")
        self.download_limit = float("inf")

        self.encrypted_dirs = set()
        self.targets = []
        self.allowed_paths = []

    @staticmethod
    def load(path_or_file):
        config = Config()

        tokenizer = Tokenizer()
        parser = Parser()

        try:
            if isinstance(path_or_file, (str, bytes,)):
                with open(path_or_file) as f:
                    for line in f:
                        tokenizer.parse_string(line, parser.tokens)
            else:
                for line in path_or_file:
                    tokenizer.parse_string(line, parser.tokens)

            tokenizer.end(parser.tokens)

            ast = parser.parse()

            program = ConfigProgram([])
            program.namespace = ConfigNamespace()
            ast2program(ast, program)

            program.evaluate(config)
        except ValueError as e:
            raise InvalidConfigError(str(e))

        return config
