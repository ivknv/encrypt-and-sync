#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import io
import json
import os
import tempfile

from functools import lru_cache

from ..EncScript import Parser, Tokenizer, ast2program
from ..EncScript.Exceptions import EncScriptError, ASTConversionError, EvaluationError
from ..constants import TEMP_ENCRYPT_BUFFER_LIMIT
from .. import Encryption
from .. import Paths
from .. import PathMatch
from ..common import get_file_size

from .Exceptions import InvalidConfigError
from .ConfigProgram import ConfigProgram
from .utils import load_encrypted_data, store_encrypted_data, check_master_key

__all__ = ["Config"]

try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError

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
        self._allowed_paths = {} # Uncompiled
        self.allowed_paths = {} # Compiled

        self.encrypted_data = {}
        self.storages = {}

        self._master_key = b""

    @property
    def upload_timeout(self):
        if self._upload_timeout is not None:
            return self._upload_timeout

        return self.timeout

    @upload_timeout.setter
    def upload_timeout(self, value):
        self._upload_timeout = value

    @property
    def master_password(self):
        raise AttributeError("can't get attribute")

    @master_password.setter
    def master_password(self, value):
        self._master_key = self.encode_key(value)

    @property
    def master_key(self):
        return self._master_key

    @property
    def plain_key(self):
        return self.encrypted_data.get("key", "")

    @plain_key.setter
    def plain_key(self, value):
        self.encrypted_data["key"] = value

    @staticmethod
    @lru_cache(maxsize=2)
    def encode_key(plain_key):
        return hashlib.sha256(plain_key.encode("utf8")).digest()

    @property
    def key(self):
        return self.encode_key(self.plain_key)

    def identify_target(self, storage_name, path, dir_type=None):
        best_match = None
        best_dir = None
        best_path = None

        if dir_type is None:
            dir_types = ("src", "dst")
        else:
            dir_types = (dir_type,)

        for target in self.targets.values():
            for d in dir_types:
                if target[d]["name"] != storage_name:
                    continue

                prefix = target[d]["path"]

                if best_path is None:
                    if Paths.contains(prefix, path):
                        best_match, best_dir = target, d
                        best_path = target[d]["path"]
                elif Paths.contains(prefix, best_path):
                    best_match, best_dir = target, d
                    best_path = target[d]["path"]

        return best_match, best_dir

    def check_master_key(self, path_or_file):
        return check_master_key(self.master_key, path_or_file)

    def check_master_password(self, path_or_file):
        return self.check_master_key(path_or_file)

    def temp_encrypt(self, in_file):
        size = get_file_size(in_file)

        if size < TEMP_ENCRYPT_BUFFER_LIMIT:
            f = io.BytesIO()
        else:
            f = tempfile.TemporaryFile(mode="w+b")

        Encryption.encrypt_file(in_file, f, self.key)
        f.seek(0)

        return f

    def temp_decrypt(self, in_file):
        size = get_file_size(in_file)

        if size < TEMP_ENCRYPT_BUFFER_LIMIT:
            f = io.BytesIO()
        else:
            f = tempfile.TemporaryFile(mode="w+b")

        Encryption.decrypt_file(in_file, f, self.key)
        f.seek(0)

        return f

    def decrypt_file(self, in_file, out_file):
        Encryption.decrypt_file(in_file, out_file, self.key)

    def encrypt_path(self, path, prefix=None, IVs=b"", filename_encoding="base64"):
        return Encryption.encrypt_path(path, self.key, prefix, ivs=IVs,
                                       filename_encoding=filename_encoding)

    def decrypt_path(self, path, prefix=None, filename_encoding="base64"):
        return Encryption.decrypt_path(path, self.key, prefix,
                                       filename_encoding=filename_encoding)    

    def load_encrypted_data(self, path_or_file, enable_test=True):
        self.encrypted_data = load_encrypted_data(path_or_file, self.master_key, enable_test)
        self.plain_key = self.encrypted_data.get("key", self.plain_key)

        return self.encrypted_data
        
    def store_encrypted_data(self, path_or_file, enable_test=True):
        store_encrypted_data(self.encrypted_data, path_or_file, self.master_key, enable_test)

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

        config._allowed_paths = config.allowed_paths
        config.allowed_paths = {}

        for k, v in config._allowed_paths.items():
            config.allowed_paths[k] = PathMatch.compile_patterns(v)

        return config
