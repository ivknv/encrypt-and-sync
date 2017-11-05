#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from ..EncScript import Parser, Tokenizer, ast2program
from ..EncScript.Exceptions import EncScriptError
from .Exceptions import InvalidConfigError
from .ConfigProgram import ConfigProgram

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
                path_or_file = os.path.realpath(path_or_file)

                tokenizer.path = path_or_file
                parser.path = path_or_file

                with open(path_or_file) as f:
                    for line in f:
                        tokenizer.parse_string(line, parser.tokens)
            else:
                for line in path_or_file:
                    tokenizer.parse_string(line, parser.tokens)

            tokenizer.end(parser.tokens)

            ast = parser.parse()

            program = ConfigProgram([])
            ast2program(ast, program)

            program.evaluate(config)
        except EncScriptError as e:
            raise InvalidConfigError(str(e))

        return config
