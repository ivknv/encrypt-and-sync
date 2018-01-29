#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import hashlib
import tempfile
import io

from . import Encryption
from . import Paths
from .Config import Config
from . import PathMatch
from .common import get_file_size

__all__ = ["EncSync", "EncSyncError", "InvalidEncryptedDataError",
           "WrongMasterKeyError"]

try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError

CONFIG_TEST = b"TEST STRING\n"

TEMP_ENCRYPT_BUFFER_LIMIT = 80 * 1024**2 # In bytes

class EncSyncError(Exception):
    pass

class InvalidEncryptedDataError(EncSyncError):
    pass

class WrongMasterKeyError(EncSyncError):
    pass

class EncSync(object):
    def __init__(self, master_key):
        self.targets = {}
        self.plain_key = ""
        self._key = ""
        self.set_master_key(master_key)

        self.encrypted_data = {}

        self.storages = {}

        self.upload_limit = float("inf")
        self.download_limit = float("inf")
        self.timeout = (15.0, 30.0)
        self._upload_timeout = None
        self.n_retries = 5
        self.sync_threads = 1
        self.download_threads = 1
        self.scan_threads = 1
        self.allowed_paths = {} # Compiled
        self._allowed_paths = {} # Uncompiled

    @property
    def upload_timeout(self):
        if self._upload_timeout is not None:
            return self._upload_timeout

        return self.timeout

    @upload_timeout.setter
    def upload_timeout(self, value):
        self._upload_timeout = value

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

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self.plain_key = key
        self._key = hashlib.sha256(key.encode("utf8")).digest()

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
        config.download_limit   = self.download_limit
        config.upload_limit     = self.upload_limit
        config.timeout          = self.timeout
        config.upload_timeout   = self.upload_timeout
        config.n_retries        = self.n_retries
        config.sync_threads     = self.sync_threads
        config.scan_threads     = self.scan_threads
        config.download_threads = self.download_threads
        config.allowed_paths    = self._allowed_paths

        for i in config.targets:
            i["allowed_paths"] = i["_allowed_paths"]

        return config

    def make_encrypted_data(self):
        d = dict(self.encrypted_data)
        d["key"] = self.plain_key

        return d

    def set_encrypted_data(self, enc_data):
        self.key = enc_data["key"]
        self.encrypted_data = enc_data

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
        self.download_limit = config.download_limit
        self.upload_limit = config.upload_limit
        self.timeout = config.timeout
        self.upload_timeout = config.upload_timeout
        self.n_retries = config.n_retries
        self.sync_threads = config.sync_threads
        self.download_threads = config.download_threads
        self.scan_threads = config.scan_threads
        self._allowed_paths = config.allowed_paths
        self.allowed_paths = {}

        for k, v in self._allowed_paths.items():
            self.allowed_paths[k] = PathMatch.compile_patterns(v)

        for target in self.targets.values():
            target["_allowed_paths"] = target["allowed_paths"]

            for k, v in target["_allowed_paths"].items():
                target["allowed_paths"][k] = PathMatch.compile_patterns(v)


            for k in ("src", "dst"):
                path = target[k]["path"]
                path = Paths.dir_normalize(Paths.join_properly("/", path))
                target[k]["path"] = path

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
