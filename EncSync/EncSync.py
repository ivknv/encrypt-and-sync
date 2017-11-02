#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import hashlib
import tempfile
import io
import yadisk

from . import Encryption
from . import Paths
from .Config import Config
from . import PathMatch

try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError

def expand_path(path):
    return os.path.realpath(os.path.expanduser(path))

def chunk(b, n):
    n = int(n)
    for i in range(int(len(b) // n)):
        yield b[i * n:(i + 1) * n]

APP_ID = "59c915d2c2d546d3842f2c6fe3a9678e"
APP_SECRET = "faca3ddd1d574e54a258aa5d8e521c8d"

CONFIG_TEST = b"TEST STRING\n"

TEMP_ENCRYPT_BUFFER_LIMIT = 80 * 1024**2 # In bytes

class EncSyncError(BaseException):
    pass

class InvalidEncryptedDataError(EncSyncError):
    pass

class WrongMasterKeyError(EncSyncError):
    pass

class EncSync(object):
    def __init__(self, master_key):
        self.targets = []
        self.plain_key = ""
        self.key = ""
        self.set_master_key(master_key)
        self.ynd_id = APP_ID
        self.ynd_token = ""
        self.ynd_secret = APP_SECRET
        self.ynd = yadisk.YaDisk(self.ynd_id, self.ynd_secret, "")

        self.upload_limit = float("inf")
        self.download_limit = float("inf")
        self.sync_threads = 1
        self.download_threads = 1
        self.scan_threads = 1
        self.encrypted_dirs = set()
        self.allowed_paths = [] # Compiled
        self._allowed_paths = [] # Uncompiled

    def find_encrypted_dir(self, path):
        p = "/"
        for i in ("/" + path).split("/"):
            p = Paths.dir_normalize(Paths.join_properly(p, i))
            if p in self.encrypted_dirs:
                return p

    def set_token(self, token):
        self.ynd_token = token
        self.ynd = yadisk.YaDisk(self.ynd_id, self.ynd_secret, self.ynd_token)

    def set_key(self, key):
        self.plain_key = key
        self.key = hashlib.sha256(key.encode("utf8")).digest()

    def set_master_key(self, master_key):
        self.master_key = hashlib.sha256(master_key.encode("utf8")).digest()

    @staticmethod
    def check_master_key(master_key, enc_data_path):
        with open(enc_data_path, "rb") as f:
            data = Encryption.decrypt_data(f.read(), master_key)
            return data[:len(CONFIG_TEST)] == CONFIG_TEST

    def make_config(self):
        config = Config()
        config.targets          = self.targets
        config.encrypted_dirs   = self.encrypted_dirs
        config.download_limit   = self.download_limit
        config.upload_limit     = self.upload_limit
        config.sync_threads     = self.sync_threads
        config.scan_threads     = self.scan_threads
        config.download_threads = self.download_threads
        config.allowed_paths    = self._allowed_paths

        for i in config.targets:
            i["allowed_paths"] = i["_allowed_paths"]

        return config

    def make_encrypted_data(self):
        return {"key":            self.plain_key,
                "yandexAppToken": self.ynd_token}

    def set_encrypted_data(self, enc_data):
        self.set_key(enc_data["key"])
        self.set_token(enc_data["yandexAppToken"])

    @staticmethod
    def load_encrypted_data(path, master_key, enable_test=True):
        with open(path, "rb") as f:
            data = f.read()

            if master_key is not None:
                data = Encryption.decrypt_data(data, master_key)

            test_string = data[:len(CONFIG_TEST)]

            if test_string != CONFIG_TEST:
                if master_key is not None:
                    raise WrongMasterKeyError("wrong master key")
                elif enable_test:
                    raise InvalidEncryptedDataError("test string is missing")
            else:
                data = data[len(CONFIG_TEST):]

            try:
                data = data.decode("utf8")
            except UnicodeDecodeError:
                raise InvalidEncryptedDataError("failed to decode")

            try:
                enc_data = json.loads(data)
            except JSONDecodeError:
                raise InvalidEncryptedDataError("not proper JSON")

            return enc_data

    @staticmethod
    def store_encrypted_data(enc_data, path, master_key, enable_test=True):
        js = json.dumps(enc_data).encode("utf8")

        if enable_test:
            js = CONFIG_TEST + js

        if master_key is not None:
            js = Encryption.encrypt_data(js, master_key)

        with open(path, "wb") as f:
            f.write(js)

    @staticmethod
    def load_config(path):
        return Config.load(path)

    def set_config(self, config):
        self.targets = config.targets
        self.encrypted_dirs = config.encrypted_dirs
        self.download_limit = config.download_limit
        self.upload_limit = config.upload_limit
        self.sync_threads = config.sync_threads
        self.download_threads = config.download_threads
        self.scan_threads = config.scan_threads
        self._allowed_paths = config.allowed_paths
        self.allowed_paths = PathMatch.compile_patterns(self._allowed_paths)

        for target in self.targets:
            self.encrypted_dirs.add(Paths.dir_normalize(target["remote"]))
            target["_allowed_paths"] = target["allowed_paths"]
            target["allowed_paths"]  = PathMatch.compile_patterns(target["_allowed_paths"])

    def temp_encrypt(self, path):
        size = os.path.getsize(path)
        if size < TEMP_ENCRYPT_BUFFER_LIMIT:
            f = io.BytesIO()
        else:
            f = tempfile.TemporaryFile(mode="w+b")
        Encryption.encrypt_file(path, f, self.key)
        f.seek(0)
        return f

    def temp_decrypt(self, path):
        size = os.path.getsize(path)
        if size < TEMP_ENCRYPT_BUFFER_LIMIT:
            f = io.BytesIO()
        else:
            f = tempfile.TemporaryFile(mode="w+b")
        Encryption.decrypt_file(path, f, self.key)
        f.seek(0)
        return f

    def decrypt_file(self, in_path, out_path):
        Encryption.decrypt_file(in_path, out_path, self.key)

    def encrypt_path(self, path, prefix=None, IVs=b""):
        return Encryption.encrypt_path(path, self.key, prefix, ivs=IVs)

    def decrypt_path(self, path, prefix=None):
        return Encryption.decrypt_path(path, self.key, prefix)    
