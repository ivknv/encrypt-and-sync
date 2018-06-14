#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest
from eas import pathm

def is_win():
    return sys.platform.startswith("win")

class PathmTestCase(unittest.TestCase):
    def test_dir_normalize(self):
        self.assertEqual(pathm.dir_normalize("/a/b"), "/a/b/")
        self.assertEqual(pathm.dir_normalize("/a/b/"), "/a/b/")
        self.assertEqual(pathm.dir_normalize("/"), "/")
        self.assertEqual(pathm.dir_normalize(""), "/")
        self.assertEqual(pathm.dir_normalize("a/b"), "a/b/")
        self.assertEqual(pathm.dir_normalize("a/b/"), "a/b/")

    def test_dir_denormalize(self):
        self.assertEqual(pathm.dir_denormalize("/a/b/"), "/a/b")
        self.assertEqual(pathm.dir_denormalize("/a/b"), "/a/b")
        self.assertEqual(pathm.dir_denormalize(""), "")
        self.assertEqual(pathm.dir_denormalize("a////"), "a")
        self.assertEqual(pathm.dir_denormalize("/"), "")
        self.assertEqual(pathm.dir_denormalize("///////"), "")

    def test_contains(self):
        self.assertFalse(pathm.contains("b/c", "/a/b/c/d"))
        self.assertFalse(pathm.contains("/b/c/d", "/a/b/c/d"))
        self.assertTrue(pathm.contains("/a/b", "/a/b/c/d"))
        self.assertTrue(pathm.contains("/a/b", "/a/b/c/d/"))
        self.assertFalse(pathm.contains("a/b", "/a/b/c/d"))
        self.assertTrue(pathm.contains("/a/b/c/d", "/a/b/c/d"))
        self.assertTrue(pathm.contains("/a/b/c/d", "/a/b/c/d/"))

    def test_join(self):
        self.assertEqual(pathm.join(None, None), "/")
        self.assertEqual(pathm.join(None, ""), "/")
        self.assertEqual(pathm.join(None, "a/b/c"), "/a/b/c")
        self.assertEqual(pathm.join("", None), "/")
        self.assertEqual(pathm.join("", ""), "/")
        self.assertEqual(pathm.join("", "a/b/c"), "/a/b/c")
        self.assertEqual(pathm.join("/a/b/c", ""), "/a/b/c/")
        self.assertEqual(pathm.join("/a/b/c", None), "/a/b/c/")
        self.assertEqual(pathm.join("/a/b/c", "d"), "/a/b/c/d")
        self.assertEqual(pathm.join("/a/b/c", "d/"), "/a/b/c/d/")
        self.assertEqual(pathm.join("/a/b/c", "/d"), "/a/b/c/d")

    def test_join_properly(self):
        self.assertEqual(pathm.join_properly("/a/b", "c/d"), "/a/b/c/d")
        self.assertEqual(pathm.join_properly("/a/b/c", "/a"), "/a")
        self.assertEqual(pathm.join_properly("/a/b/c", "d/"), "/a/b/c/d/")
        self.assertEqual(pathm.join_properly("/a/b/c", ""), "/")
        self.assertEqual(pathm.join_properly("a/b/c", "./d"), "a/b/c/d")
        self.assertEqual(pathm.join_properly("a/b/c", ".././"), "a/b/")
        self.assertEqual(pathm.join_properly("/", ".."), "/")

    def test_cut_off(self):
        self.assertEqual(pathm.cut_off("/a/b/c/d", "b/c/d"), "/a/")
        self.assertEqual(pathm.cut_off("/a/b/c/d", "/b/c/d"), "/a")
        self.assertEqual(pathm.cut_off("/a/b/c/d", "/a/c"), "/a/b/c/d")
        self.assertEqual(pathm.cut_off("/a/b/c/def", "def"), "/a/b/c/")
        self.assertEqual(pathm.cut_off("/a/b/c/def/e", "c/def"), "/a/b/c/def/e")

    def test_cut_prefix(self):
        self.assertEqual(pathm.cut_prefix("/a/b/c/d", "/a/b"), "c/d")
        self.assertEqual(pathm.cut_prefix("/a/b/c/d", "/b/c"), "/a/b/c/d")
        self.assertEqual(pathm.cut_prefix("/a/b/c/d", "/a/b/"), "c/d")
        self.assertEqual(pathm.cut_prefix("/a/b/c/d", "/a/b/c/d"), "")
        self.assertEqual(pathm.cut_prefix("/a/b", "/a/b/"), "")
        self.assertEqual(pathm.cut_prefix("", ""), "")

    def test_split(self):
        self.assertEqual(pathm.split("/a/b/c"), ("/a/b", "c"))
        self.assertEqual(pathm.split("/a/b/c/"), ("/a/b", "c"))
        self.assertEqual(pathm.split(""), ("/", ""))
        self.assertEqual(pathm.split("/"), ("/", ""))
        self.assertEqual(pathm.split("/a/"), ("/", "a"))
        self.assertEqual(pathm.split("a/"), ("a", ""))

    def test_explicit(self):
        if is_win():
            drive_letter = os.path.abspath("/")[0]

            self.assertEqual(pathm.explicit("/a/b/c"), "/%s/a/b/c" % (drive_letter,))
            self.assertEqual(pathm.explicit("b/c"), "b/c")
            self.assertEqual(pathm.explicit(""), "/%s/" % (drive_letter,))
            self.assertEqual(pathm.explicit("/"), "/%s/" % (drive_letter,))
            self.assertEqual(pathm.explicit("C:/a/b/c"), "/C/a/b/c")
            self.assertEqual(pathm.explicit("D:/c/d/e/"), "/D/c/d/e/")
            self.assertEqual(pathm.explicit("d:/c/d/e"), "/D/c/d/e")
            self.assertEqual(pathm.explicit("c:/a/b/c"), "/C/a/b/c")
        else:
            self.assertEqual(pathm.explicit("/a/b/c"), "/a/b/c")
            self.assertEqual(pathm.explicit("/"), "/")
            self.assertEqual(pathm.explicit("b/c"), "b/c")
            self.assertEqual(pathm.explicit(""), "/")

    def test_from_sys(self):
        if not is_win():
            return

        drive_letter = os.path.abspath("/")[0]

        self.assertEqual(pathm.from_sys(r"C:\a\b\c"), "/C/a/b/c")
        self.assertEqual(pathm.from_sys(r"Z:\a\b\c"), "/Z/a/b/c")
        self.assertEqual(pathm.from_sys("C:/a/b/c"), "/C/a/b/c")
        self.assertEqual(pathm.from_sys("/a/b/c"), "/%s/a/b/c" % (drive_letter,))
        self.assertEqual(pathm.from_sys(r"/a\b/c"), "/%s/a/b/c" % (drive_letter,))

    def test_to_sys(self):
        if not is_win():
            return

        self.assertEqual(pathm.to_sys("/C/a/b/c"), r"C:\a\b\c")
        self.assertEqual(pathm.to_sys("/D/a/b/c"), r"D:\a\b\c")
        self.assertEqual(pathm.to_sys("/Z/c/d/e/"), "Z:\\c\\d\\e\\")

    def test_is_equal(self):
        self.assertTrue(pathm.is_equal("", ""))
        self.assertTrue(pathm.is_equal("/", ""))
        self.assertTrue(pathm.is_equal("", "/"))
        self.assertTrue(pathm.is_equal("///", "/"))
        self.assertTrue(pathm.is_equal("/a/b/d/e", "/a/b/d/e/"))
        self.assertTrue(pathm.is_equal("/a/b/d/e/", "/a/b/d/e/"))
        self.assertTrue(pathm.is_equal("/a/b/d/e/./.", "/a/b/d/e/"))
        self.assertTrue(pathm.is_equal("/a/b/d/e/././../", "/a/b/d"))
        self.assertTrue(pathm.is_equal("./a", "a"))

        self.assertFalse(pathm.is_equal("/", "/a/b/d"))
        self.assertFalse(pathm.is_equal("/a/b/c", "/c/b/a"))
        self.assertFalse(pathm.is_equal("/a/b/c/..", "/c/b/a"))
