# -*- coding: utf-8 -*-

__all__ = ["YADISK_APP_ID", "YADISK_APP_SECRET", "DROPBOX_APP_KEY",
           "DROPBOX_APP_SECRET", "DEFAULT_UPLOAD_TIMEOUT",
           "TEMP_ENCRYPT_BUFFER_LIMIT", "FILENAME_ENCODINGS"]

YADISK_APP_ID = "59c915d2c2d546d3842f2c6fe3a9678e"
YADISK_APP_SECRET = "faca3ddd1d574e54a258aa5d8e521c8d"

DROPBOX_APP_KEY = "n2nw2j5vmkactty"
DROPBOX_APP_SECRET = "d7t7g0kqlbqeb8j"

DEFAULT_UPLOAD_TIMEOUT = (10.0, 60.0)

# Used by EncSync.temp_encrypt() and EncSync.temp_decrypt()
TEMP_ENCRYPT_BUFFER_LIMIT = 80 * 1024**2 # In bytes

# Test string used to verify whether the file was decrypted with the correct key
CONFIG_TEST = b"TEST STRING\n"

FILENAME_ENCODINGS = ("base64", "base41")
