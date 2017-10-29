#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import unittest

from EncSync.EncPath import EncPath
from EncSync.EncSync import EncSync
from EncSync import Paths

def get_encsync():
    encsync = EncSync(os.environ.get("ENCSYNC_MASTER_PASSWORD", ""))
    encsync.set_encrypted_data(
        encsync.load_encrypted_data(os.path.expanduser("~/.encsync/encrypted_data.json"),
                                    encsync.master_key))
    encsync.set_config(encsync.load_config(os.path.expanduser("~/.encsync/encsync.conf")))

    return encsync

class EncPathTestCase(unittest.TestCase):
    def setUp(self):
        self.encsync = get_encsync()

    def test_encryption(self):
        e = EncPath(self.encsync)
        e.local_prefix = Paths.to_sys("/local/")
        e.remote_prefix = "/remote/"
        e.path = "a/b/c"

        self.assertEqual(e.local, "/local/a/b/c")
        self.assertEqual(e.remote, "/remote/a/b/c")
        self.assertEqual(self.encsync.decrypt_path(e.remote_enc, e.remote_prefix),
                         (e.remote, e.IVs))
        self.assertEqual(self.encsync.decrypt_path(e.path_enc), (e.path, e.IVs))

        e = EncPath(self.encsync)
        e.remote_prefix = "/remote"
        e.path = "/a/b/c"
        e.IVs = b"0123456789ABCDEF" * 3

        self.assertEqual(self.encsync.decrypt_path(e.path_enc), (e.path, e.IVs))
        self.assertEqual(e.IVs, b"0123456789ABCDEF" * 3)
        self.assertEqual(self.encsync.decrypt_path(e.remote_enc, e.remote_prefix), (e.remote, e.IVs))

        e.IVs = None

        self.assertIsNotNone(e.IVs)

        e.IVs = b""
        e.path_enc

        self.assertEqual(len(e.IVs), 16 * 3)

        e.IVs = b"1" * 16
        e.path_enc

        self.assertEqual(len(e.IVs), 16 * 3)
        self.assertEqual(e.IVs[:16], b"1" * 16)

    def test_decryption(self):
        e = EncPath(self.encsync)
        e.path_enc = "Dw96rjT89MIEIqaSkWfNuFE9olpB0AluyieMjNkM_n3h/D3yrqtxmgrpm1snq38l_1plthCv-YRh4KW7KC11-dOzP/D9RXh_LhOYNaetS8z_NPRCsXF-VFPCl6ausEujfDmk2x"

        self.assertEqual(e.path, "a/b/c")
        self.assertTrue(e.IVs not in (None, b""))
        self.assertEqual(len(e.IVs), 16 * 3)

    def test_copy(self):
        e = EncPath(self.encsync)
        e.local_prefix = "/local/"
        e.remote_prefix = "/remote/"
        e.path = "a/b/c"
        e.IVs = b"1" * (16 * 3)

        c = e.copy()

        self.assertEqual(e.path, c.path)
        self.assertEqual(e.local_prefix, c.local_prefix)
        self.assertEqual(e.remote_prefix, c.remote_prefix)
        self.assertEqual(e.IVs, c.IVs)
        self.assertEqual(e.remote, c.remote)
        self.assertEqual(e.local, c.local)
        self.assertEqual(e.path_enc, c.path_enc)
        self.assertEqual(e.remote_enc, c.remote_enc)
