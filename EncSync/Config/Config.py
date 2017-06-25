#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Tokenizer import Tokenizer
from .Parser import Parser, AST
from .Exceptions import InvalidConfigError

from . import commands, blocks

class Config(object):
    word_map = {"sync-threads":     commands.set_sync_threads,
                "scan-threads":     commands.set_scan_threads,
                "download-threads": commands.set_download_threads,
                "upload-limit":     commands.set_upload_limit,
                "download-limit":   commands.set_download_limit}
    block_map = {"targets":        blocks.exec_targets_block,
                 "encrypted-dirs": blocks.exec_encrypted_dirs_block}

    def __init__(self):
        self.sync_threads = 1
        self.scan_threads = 1
        self.download_threads = 1
        self.upload_limit = float("inf")
        self.download_limit = float("inf")

        self.encrypted_dirs = set()
        self.targets = []

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

            interpret_ast(config, ast)
        except ValueError as e:
            raise InvalidConfigError(str(e))

        return config

    def validate(self):
        for k, v in {"sync_threads":     self.sync_threads,
                     "scan_threads":     self.scan_threads,
                     "download_threads": self.download_threads}.items():
            if not is_positive_int(v):
                return False, "%r must be a positive integer" % k

        for k, v in {"upload_limit":   self.upload_limit,
                     "download_limit": self.download_limit}.items():
            if not isinstance(v, (int, float)):
                return False, "%r must be an instance of int or float" % k
            elif v < 0:
                return False, "%r must be positive" % k
            elif v != v:
                return False, "%r must not be NaN" % k

        target_fields = {"local":  str,
                         "remote": str,
                         "name":   (str, None)}

        for target in self.targets:
            if not isinstance(target, dict):
                return False, "target must be an instance of dict"

            for field, types in target_fields.items():
                if field not in target:
                    return False, "target is missing %r field" % field
                elif not isinstance(target[field], types):
                    if isinstance(types, tuple):
                        return False, "target field %r must be of types %r" % (field, types,)
                    else:
                        return False, "target field %r must be of type %r" % (field, types,)

        if not isinstance(self.encrypted_dirs, (set, list)):
            return False, "'encrypted_dirs' must be an instance of set or list"

        for path in self.encrypted_dirs:
            if not isinstance(path, str):
                return False, "'encrypted_dirs': path must be an instance of str"

        return True, "no errors"

def interpret_ast(config, ast):
    for child in ast.children:
        assert(child.type in (AST.COMMAND, AST.BLOCK, AST.END))

        if child.type == AST.COMMAND:
            interpret_command(config, child)
        elif child.type == AST.BLOCK:
            interpret_block(config, child)

def interpret_command(config, ast):
    command = ast2command(ast)

    if not command:
        return

    try:
        func = Config.word_map[command[0]]
    except KeyError:
        raise ValueError("Unknown word: %r" % command[0])

    func(config, command[1:])

def interpret_block(config, ast):
    child = ast.children[0]
    assert(child.type == AST.SIMPLEWORD)

    block_name = child.token.string
    args = []
    commands = []

    for child in ast.children[1:]:
        assert(child.type in (AST.SIMPLEWORD, AST.WORD, AST.LCBR, AST.COMMAND, AST.RCBR))

        if child.type in (AST.SIMPLEWORD, AST.WORD):
            args.append(child.token.string)
        elif child.type == AST.COMMAND:
            command = ast2command(child)
            if command:
                commands.append(command)

    try:
        func = Config.block_map[block_name]
    except KeyError:
        raise ValueError("Unknown block name: %r" % block_name)

    func(config, args, commands)

def ast2command(ast):
    command = []

    for child in ast.children:
        assert(child.type in (AST.WORD, AST.SIMPLEWORD, AST.SEP))

        if child.type in (AST.WORD, AST.SIMPLEWORD):
            command.append(child.token.string)

    return command

def is_positive_int(x):
    return isinstance(x, int) and x > 0
