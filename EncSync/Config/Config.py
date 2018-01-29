#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from ..EncScript import Parser, Tokenizer, ast2program
from ..EncScript.Exceptions import EncScriptError, ASTConversionError, EvaluationError
from .Exceptions import InvalidConfigError
from .ConfigProgram import ConfigProgram

__all__ = ["Config"]

class Config(object):
    def __init__(self):
        self.sync_threads = 1
        self.scan_threads = 1
        self.download_threads = 1
        self.upload_limit = float("inf")
        self.download_limit = float("inf")
        self.timeout = (15.0, 30.0)
        self._upload_timeout = None
        self.n_retries = 5

        self.targets = {}
        self.allowed_paths = {}

    @property
    def upload_timeout(self):
        if self._upload_timeout is not None:
            return self._upload_timeout

        return self.timeout

    @upload_timeout.setter
    def upload_timeout(self, value):
        self._upload_timeout = value

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
        except EncScriptError as e:
            raise InvalidConfigError(str(e))

        program = ConfigProgram([])
        program.line_num = 1
        program.char_num = 1

        try:
            ast2program(ast, program)
        except ASTConversionError as e:
            if isinstance(path_or_file, (str, bytes)):
                location = "%s:%d:%d" % (path_or_file, e.ast.line_num, e.ast.char_num)
            else:
                location = "%d:%d" % (e.ast.line_num, e.ast.char_num)

            raise InvalidConfigError("At %s: %s" % (location, str(e)))

        try:
            program.evaluate(config)
        except EvaluationError as e:
            if isinstance(path_or_file, (str, bytes)):
                location = "%s:%d:%d" % (path_or_file, e.node.line_num, e.node.char_num)
            else:
                location = "%d:%d" % (e.node.line_num, e.node.char_num)

            raise InvalidConfigError("At %s: %s" % (location, str(e)))

        return config
