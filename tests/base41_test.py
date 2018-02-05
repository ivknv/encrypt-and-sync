#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import unittest

from EncSync.Encryption.filename_encodings import base41_encode, base41_decode

def random_bytes(a, b):
    return bytes(random.randint(0, 255) for i in range(a, b))

class Base41TestCase(unittest.TestCase):
    def setUp(self):
        self.data = {b"test":         b"coqciv",
                     b"1234":         b"3f33ro",
                     b"":             b"",
                     b"0":            b",3=",
                     b"what":         b"d3i_tf",
                     b"\x00\x00":     b"++=",
                     b"\xff\xff":     b"xzc",
                     b"\x00\xff":     b"+25",
                     b"\xff":         b"25=",
                     b"\xff\x00":     b"xt4",
                     b"test message": b"coqciv0xeaddcicapj",
                     b"\x01\x02\x03": b"28=.=="}

    def test_encode(self):
        for k, v in self.data.items():
            self.assertEqual(base41_encode(k), v)

    def test_decode(self):
        for k, v in self.data.items():
            self.assertEqual(base41_decode(v), k)

        self.assertEqual(base41_decode(b"==="), b"")

        with self.assertRaises(ValueError):
            base41_decode(b"xzd")

        with self.assertRaises(ValueError):
            base41_decode(b"zzz")

        with self.assertRaises(ValueError):
            base41_decode(b"a=")

        with self.assertRaises(ValueError):
            base41_decode(b"a=b")

    def test_random(self):
        for i in range(1000):
            byte_string = random_bytes(0, 50)
            encoded = base41_encode(byte_string)
            decoded = base41_decode(encoded)

            self.assertEqual(decoded, byte_string)
