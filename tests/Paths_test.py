#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest
from EncSync import Paths

def is_win():
    return sys.platform.startswith("win")

class PathsTestCase(unittest.TestCase):
    def test_dir_normalize(self):
        self.assertEqual(Paths.dir_normalize("/a/b"), "/a/b/")
        self.assertEqual(Paths.dir_normalize("/a/b/"), "/a/b/")
        self.assertEqual(Paths.dir_normalize("/"), "/")
        self.assertEqual(Paths.dir_normalize(""), "/")
        self.assertEqual(Paths.dir_normalize("a/b"), "a/b/")
        self.assertEqual(Paths.dir_normalize("a/b/"), "a/b/")

    def test_dir_denormalize(self):
        self.assertEqual(Paths.dir_denormalize("/a/b/"), "/a/b")
        self.assertEqual(Paths.dir_denormalize("/a/b"), "/a/b")
        self.assertEqual(Paths.dir_denormalize(""), "")
        self.assertEqual(Paths.dir_denormalize("a////"), "a")
        self.assertEqual(Paths.dir_denormalize("/"), "")
        self.assertEqual(Paths.dir_denormalize("///////"), "")

    def test_contains(self):
        self.assertFalse(Paths.contains("b/c", "/a/b/c/d"))
        self.assertFalse(Paths.contains("/b/c/d", "/a/b/c/d"))
        self.assertTrue(Paths.contains("/a/b", "/a/b/c/d"))
        self.assertTrue(Paths.contains("/a/b", "/a/b/c/d/"))
        self.assertFalse(Paths.contains("a/b", "/a/b/c/d"))
        self.assertTrue(Paths.contains("/a/b/c/d", "/a/b/c/d"))
        self.assertTrue(Paths.contains("/a/b/c/d", "/a/b/c/d/"))

    def test_join(self):
        self.assertEqual(Paths.join(None, None), "/")
        self.assertEqual(Paths.join(None, ""), "/")
        self.assertEqual(Paths.join(None, "a/b/c"), "/a/b/c")
        self.assertEqual(Paths.join("", None), "/")
        self.assertEqual(Paths.join("", ""), "/")
        self.assertEqual(Paths.join("", "a/b/c"), "/a/b/c")
        self.assertEqual(Paths.join("/a/b/c", ""), "/a/b/c/")
        self.assertEqual(Paths.join("/a/b/c", None), "/a/b/c/")
        self.assertEqual(Paths.join("/a/b/c", "d"), "/a/b/c/d")
        self.assertEqual(Paths.join("/a/b/c", "d/"), "/a/b/c/d/")
        self.assertEqual(Paths.join("/a/b/c", "/d"), "/a/b/c/d")

    def test_join_properly(self):
        self.assertEqual(Paths.join_properly("/a/b", "c/d"), "/a/b/c/d")
        self.assertEqual(Paths.join_properly("/a/b/c", "/a"), "/a")
        self.assertEqual(Paths.join_properly("/a/b/c", "d/"), "/a/b/c/d/")
        self.assertEqual(Paths.join_properly("/a/b/c", ""), "/")
        self.assertEqual(Paths.join_properly("a/b/c", "./d"), "a/b/c/d")
        self.assertEqual(Paths.join_properly("a/b/c", ".././"), "a/b/")
        self.assertEqual(Paths.join_properly("/", ".."), "/")

    def test_cut_off(self):
        self.assertEqual(Paths.cut_off("/a/b/c/d", "b/c/d"), "/a/")
        self.assertEqual(Paths.cut_off("/a/b/c/d", "/b/c/d"), "/a")
        self.assertEqual(Paths.cut_off("/a/b/c/d", "/a/c"), "/a/b/c/d")
        self.assertEqual(Paths.cut_off("/a/b/c/def", "def"), "/a/b/c/")
        self.assertEqual(Paths.cut_off("/a/b/c/def/e", "c/def"), "/a/b/c/def/e")

    def test_cut_prefix(self):
        self.assertEqual(Paths.cut_prefix("/a/b/c/d", "/a/b"), "c/d")
        self.assertEqual(Paths.cut_prefix("/a/b/c/d", "/b/c"), "/a/b/c/d")
        self.assertEqual(Paths.cut_prefix("/a/b/c/d", "/a/b/"), "c/d")
        self.assertEqual(Paths.cut_prefix("/a/b/c/d", "/a/b/c/d"), "")
        self.assertEqual(Paths.cut_prefix("/a/b", "/a/b/"), "")
        self.assertEqual(Paths.cut_prefix("", ""), "")

    def test_split(self):
        self.assertEqual(Paths.split("/a/b/c"), ("/a/b", "c"))
        self.assertEqual(Paths.split("/a/b/c/"), ("/a/b", "c"))
        self.assertEqual(Paths.split(""), ("/", ""))
        self.assertEqual(Paths.split("/"), ("/", ""))
        self.assertEqual(Paths.split("/a/"), ("/", "a"))
        self.assertEqual(Paths.split("a/"), ("a", ""))

    def test_explicit(self):
        if is_win():
            drive_letter = os.path.abspath("/")[0]

            self.assertEqual(Paths.explicit("/a/b/c"), "/%s/a/b/c" % (drive_letter,))
            self.assertEqual(Paths.explicit("b/c"), "b/c")
            self.assertEqual(Paths.explicit(""), "/%s/" % (drive_letter,))
            self.assertEqual(Paths.explicit("/"), "/%s/" % (drive_letter,))
            self.assertEqual(Paths.explicit("C:/a/b/c"), "/C/a/b/c")
            self.assertEqual(Paths.explicit("D:/c/d/e/"), "/D/c/d/e/")
            self.assertEqual(Paths.explicit("d:/c/d/e"), "/D/c/d/e")
            self.assertEqual(Paths.explicit("c:/a/b/c"), "/C/a/b/c")
        else:
            self.assertEqual(Paths.explicit("/a/b/c"), "/a/b/c")
            self.assertEqual(Paths.explicit("/"), "/")
            self.assertEqual(Paths.explicit("b/c"), "b/c")
            self.assertEqual(Paths.explicit(""), "/")

    def test_from_sys(self):
        if not is_win():
            return

        drive_letter = os.path.abspath("/")[0]

        self.assertEqual(Paths.from_sys(r"C:\a\b\c"), "/C/a/b/c")
        self.assertEqual(Paths.from_sys(r"Z:\a\b\c"), "/Z/a/b/c")
        self.assertEqual(Paths.from_sys("C:/a/b/c"), "/C/a/b/c")
        self.assertEqual(Paths.from_sys("/a/b/c"), "/%s/a/b/c" % (drive_letter,))
        self.assertEqual(Paths.from_sys(r"/a\b/c"), "/%s/a/b/c" % (drive_letter,))

    def test_to_sys(self):
        if not is_win():
            return

        self.assertEqual(Paths.to_sys("/C/a/b/c"), r"C:\a\b\c")
        self.assertEqual(Paths.to_sys("/D/a/b/c"), r"D:\a\b\c")
        self.assertEqual(Paths.to_sys("/Z/c/d/e/"), "Z:\\c\\d\\e\\")
