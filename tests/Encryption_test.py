#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from EncSync import Encryption

class EncryptionTestCase(unittest.TestCase):
    def test_pad_size(self):
        self.assertEqual(Encryption.pad_size(16), 16)
        self.assertEqual(Encryption.pad_size(0), 0)
        self.assertEqual(Encryption.pad_size(7), 16)
        self.assertEqual(Encryption.pad_size(58), 64)
        self.assertEqual(Encryption.pad_size(17), 32)

    def test_encrypt_data(self):
        self.assertEqual(Encryption.encrypt_data(b"test data", b"1" * 16, b"0" * 16),
                         b"\t\x00\x00\x00\x00\x00\x00\x000000000000000000- \xdar\xf8\x86~\x90U\x19=\xe5\x997\xf6\x0f")
        
        self.assertEqual(Encryption.encrypt_data(b"something else", b"1" * 16, b"0" * 16),
                         b"\x0e\x00\x00\x00\x00\x00\x00\x000000000000000000\xfa\x07\x1f\xb2\xa0\x86`J\x8d\x98B\xa7\x11\xa84S")

        self.assertEqual(Encryption.encrypt_data(b"just a regular string", b"1" * 16, b"0" * 16),
                         b"\x15\x00\x00\x00\x00\x00\x00\x000000000000000000\x1bq\xbc\xef\xbb/\xc4\xd3\x0b\x83\x93\xf3\x02\xaaR\xa1\x97\xc9\xe4 \xeb\xb1)4\xe2\x12\x87\xe0l\x9b\x1f\x1a")

        self.assertRaises(Encryption.EncryptionError, lambda: Encryption.encrypt_data(b"", b"asd"))
        self.assertRaises(Encryption.EncryptionError, lambda: Encryption.encrypt_data("asdasd", b"1" * 16))

    def test_decrypt_data(self):
        key = b"test" * 4

        self.assertEqual(Encryption.decrypt_data(Encryption.encrypt_data(b"abc", key), key), b"abc")
        self.assertEqual(Encryption.decrypt_data(Encryption.encrypt_data(b"test", key), key), b"test")
        self.assertEqual(Encryption.decrypt_data(Encryption.encrypt_data(b"", key), key), b"")

        self.assertRaises(Encryption.DecryptionError, lambda: Encryption.decrypt_data(b"", b"3"))
        self.assertRaises(Encryption.DecryptionError, lambda: Encryption.decrypt_data(b"asdasd", key))
        self.assertRaises(Encryption.DecryptionError, lambda: Encryption.decrypt_data("asdasd", key))


    def test_encrypt_filename(self):
        key = b"test" * 4
        iv = b"42" * 8

        self.assertEqual(Encryption.encrypt_filename("test.txt", key, iv),
                         ("CDQyNDI0MjQyNDI0MjQyNDIYdvPXpX-gntcozU3abQPi", iv))
        self.assertEqual(Encryption.encrypt_filename("a-bit-longer-filename.txt", key, iv),
                         ("BzQyNDI0MjQyNDI0MjQyNDJ9e9zggYMDPkaMnWoqldI46rYpn6ChNYH6OwtaEVYDwQ==", iv))
        self.assertEqual(Encryption.encrypt_filename("a", key, iv),
                         ("DzQyNDI0MjQyNDI0MjQyNDJ2y9mPhDC5LgJpLX4IqYhj", iv))

    def test_decrypt_filename(self):
        key = b"test" * 4
        iv = b"0" * 16

        self.assertEqual(
            Encryption.decrypt_filename(Encryption.encrypt_filename("test.txt", key, iv)[0], key),
            ("test.txt", iv))
        self.assertEqual(
            Encryption.decrypt_filename(Encryption.encrypt_filename("asdasd.gz", key, iv)[0], key),
            ("asdasd.gz", iv))
        self.assertEqual(
            Encryption.decrypt_filename(Encryption.encrypt_filename("0123456789ABCDEF", key, iv)[0], key),
            ("0123456789ABCDEF", iv))

    def test_encrypt_path(self):
        key = b"1234" * 4
        iv = b"78" * 8

        self.assertEqual(Encryption.encrypt_path("/a/b/c", key, ivs=iv * 3),
                         ("/Dzc4Nzg3ODc4Nzg3ODc4Nzhco8ML30VzCM4DK8QelkAJ/Dzc4Nzg3ODc4Nzg3ODc4NzgOJL8M76jvKJ-GjEVaLhpH/Dzc4Nzg3ODc4Nzg3ODc4NzhjHZ_s6PoucOINQPyEvBWx",
                          iv * 3))
        self.assertEqual(Encryption.encrypt_path("/prefix/a/b", key, "/prefix", ivs=iv * 2),
                         ("/prefix/Dzc4Nzg3ODc4Nzg3ODc4Nzhco8ML30VzCM4DK8QelkAJ/Dzc4Nzg3ODc4Nzg3ODc4NzgOJL8M76jvKJ-GjEVaLhpH",
                          iv * 2))

        self.assertEqual(Encryption.encrypt_path("/", key), ("/", b""))
        self.assertEqual(Encryption.encrypt_path("", key), ("", b""))

        self.assertEqual(Encryption.encrypt_path("/a", key, "/a"), ("/a", b""))
        self.assertEqual(Encryption.encrypt_path("/a/", key, "/a"), ("/a/", b""))

    def test_decrypt_path(self):
        key = b"1234" * 4
        iv = b"78" * 8

        self.assertEqual(Encryption.decrypt_path(Encryption.encrypt_path("/a/b/c", key, ivs=iv * 3)[0], key),
                         ("/a/b/c", iv * 3))
        self.assertEqual(
            Encryption.decrypt_path(Encryption.encrypt_path("/prefix/a/b/c", key, "/prefix", ivs=iv * 3)[0],
                                    key, "/prefix"),
            ("/prefix/a/b/c", iv * 3))

        self.assertEqual(Encryption.decrypt_path(Encryption.encrypt_path("/", key)[0], key),
                         ("/", b""))
        self.assertEqual(Encryption.decrypt_path(Encryption.encrypt_path("", key)[0], key),
                         ("", b""))

        self.assertEqual(Encryption.decrypt_path("/a", key, "/a"), ("/a", b""))
        self.assertEqual(Encryption.decrypt_path("/a/", key, "/a"), ("/a/", b""))
