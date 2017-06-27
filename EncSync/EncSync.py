#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import hashlib
import tempfile
import io

from . import YandexDiskApi
from .YandexDiskApi.Exceptions import UnauthorizedError 
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

AUTH_URL = "https://oauth.yandex.ru/authorize?response_type=code&client_id=" + APP_ID

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
        self.ynd = YandexDiskApi.YndApi(self.ynd_id, "", self.ynd_secret)
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
        self.ynd = YandexDiskApi.YndApi(self.ynd_id, self.ynd_token, self.ynd_secret)

    def set_key(self, key):
        self.plain_key = key
        self.key = hashlib.sha256(key.encode("utf8")).digest()

    def set_master_key(self, master_key):
        self.master_key = hashlib.sha256(master_key.encode("utf8")).digest()

    def check_token(self, max_retries=1):
        try:
            r = self.ynd.get_disk_data(max_retries=max_retries)
        except UnauthorizedError:
            return False

        return True

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
        if prefix is not None:
            enc_path, IVs = self.encrypt_path(Paths.cut_prefix(path, prefix), IVs=IVs)
            if path.startswith(Paths.dir_normalize(prefix)):
                return Paths.join(prefix, enc_path), IVs
            return enc_path, IVs
        elif path == "":
            return "", b""

        f = lambda x, IV: Encryption.encrypt_filename(x, self.key, IV) if x else ("", b"")
        out_IVs = b""
        path_fragments = []

        if len(IVs):
            for fragment, IV in zip(path.split("/"), chunk(IVs, 16)):
                enc_fragment = f(fragment, IV)[0]
                path_fragments.append(enc_fragment)
                out_IVs += IV
        else:
            for fragment in path.split("/"):
                enc_fragment, IV = f(fragment, b"")
                path_fragments.append(enc_fragment)
                out_IVs += IV

        return "/".join(path_fragments), out_IVs

    def decrypt_path(self, path, prefix=None):
        if prefix is not None:
            dec_path, IVs = self.decrypt_path(Paths.cut_prefix(path, prefix))
            if path.startswith(Paths.dir_normalize(prefix)):
                return Paths.join(prefix, dec_path), IVs
            return dec_path, IVs

        f = lambda x: Encryption.decrypt_filename(x, self.key) if x else ("", b"")
        IVs = b""
        path_fragments = []

        for fragment in path.split("/"):
            dec_fragment, IV = f(fragment)
            path_fragments.append(dec_fragment)
            IVs += IV

        return "/".join(path_fragments), IVs
