#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import hashlib
import tempfile
import io

from . import YandexDiskApi
from . import Encryption
from . import Paths

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

class ConfigError(EncSyncError):
    pass

class InvalidConfigError(ConfigError):
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
        self.upload_limit = 1024**4
        self.download_limit = 1024**4
        self.sync_threads = 2
        self.download_threads = 2
        self.scan_threads = 2
        self.encrypted_dirs = set()

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
        r = self.ynd.get_disk_data(max_retries=max_retries)

        if not r["success"] and r["data"] is not None:
            return r["data"]["error"] != "UnauthorizedError"

        return True

    @staticmethod
    def check_master_key(master_key, config_path):
        with open(config_path, "rb") as f:
            data = Encryption.decrypt_data(f.read(), master_key)
            return data[:len(CONFIG_TEST)] == CONFIG_TEST

    @staticmethod
    def validate_config(config):
        required_fields = ("targets", "encryptedDirs", "downloadSpeedLimit",
                           "uploadSpeedLimit", "key", "nSyncThreads",
                           "nDownloadThreads", "nScanThreads", "yandexAppToken")

        for field in required_fields:
            if field not in config:
                return (False, "Missing field %r" % field)

        return (True, "No errors")

    def make_config(self):
        return {"targets":            self.targets,
                "encryptedDirs":      sorted(self.encrypted_dirs),
                "downloadSpeedLimit": self.download_limit,
                "uploadSpeedLimit":   self.upload_limit,
                "key":                self.plain_key,
                "nSyncThreads":       self.sync_threads,
                "nDownloadThreads":   self.download_threads,
                "nScanThreads":       self.scan_threads,
                "yandexAppToken":     self.ynd_token}

    @staticmethod
    def load_config(path, master_key, enable_test=True):
        with open(path, "rb") as f:
            data = f.read()

            if master_key is not None:
                data = Encryption.decrypt_data(data, master_key)

            test_string = data[:len(CONFIG_TEST)]

            if test_string != CONFIG_TEST:
                if master_key is not None:
                    raise WrongMasterKeyError("Wrong master key")
                elif enable_test:
                    raise InvalidConfigError("test string is missing")
            else:
                data = data[len(CONFIG_TEST):]

            try:
                data = data.decode("utf8")
            except UnicodeDecodeError:
                raise InvalidConfigError("failed to decode")

            try:
                config = json.loads(data)
            except JSONDecodeError:
                raise InvalidConfigError("not proper JSON")

            return config

    @staticmethod
    def store_config(config, path, master_key, enable_test=True):
        js = json.dumps(config, indent=4, sort_keys=True).encode("utf8")

        if enable_test:
            js = CONFIG_TEST + js

        if master_key is not None:
            js = Encryption.encrypt_data(js, master_key)

        with open(path, "wb") as f:
            f.write(js)

    def set_config(self, config):
        valid, msg = EncSync.validate_config(config)

        if not valid:
            raise InvalidConfigError("Invalid config: %s" % msg)

        self.targets = config["targets"]
        self.set_key(config["key"])

        self.encrypted_dirs = config.get("encryptedDirs", self.encrypted_dirs)

        self.encrypted_dirs = set(map(lambda x: Paths.dir_normalize(Paths.join_properly("/", x)),
                                      self.encrypted_dirs))

        self.ynd_token = config["yandexAppToken"]
        self.download_limit = config.get("downloadSpeedLimit", self.download_limit)
        self.upload_limit = config.get("uploadSpeedLimit", self.upload_limit)
        self.sync_threads = config.get("nSyncThreads", self.sync_threads)
        self.download_threads = config.get("nDownloadThreads", self.download_threads)
        self.scan_threads = config.get("nScanThreads", self.scan_threads)
        self.ynd = YandexDiskApi.YndApi(self.ynd_id, self.ynd_token, self.ynd_secret)

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
