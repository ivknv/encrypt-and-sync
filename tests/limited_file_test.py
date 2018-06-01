#!/usr/bin/env python
# -*- coding: utf-8 -*-

from io import BytesIO
import time
import unittest

from eas.storage.limited_file import LimitedFile

class PseudoController(object):
    def __init__(self, *args, **kwargs):
        self.stopped = False
        self.uploaded = 0

    def stop(self):
        self.stopped = True

class LimitedFileTestCase(unittest.TestCase):
    def _test_write_speed_limit(self, line_count, limit, read_size):
        controller = PseudoController()

        line_size = 1024
        file_size = line_size * line_count
        expected_error = 0.025

        file = BytesIO()
        file.write((b"0" * (line_size - 1) + b"\n") * line_count)
        file.seek(0)

        limited_file = LimitedFile(file, controller, limit)

        expected_time = file_size / limit

        t1 = time.time()

        line = 1
        while line:
            line = limited_file.read(read_size)

        t2 = time.time()

        error = abs((t2 - t1) - expected_time) / expected_time

        print("Time: %ss" % (t2 - t1,))
        print("Speed: %s MiB/s" % (file_size / (t2 - t1) / 1024**2,))
        print("Error: %s%%" % (error * 100.0,))
        print("Expected time: %ss" % (expected_time,))
        print("Expected speed: %s MiB/s" % (limit / 1024**2,))
        print("Expected error: < %s%%" % (expected_error * 100.0,))
        print()

        self.assertLess(error, expected_error)

    def test_write_speed_limit_small(self):
        self._test_write_speed_limit(1024, 1024**2, 100)

    def test_speed_limit_big(self):
        self._test_write_speed_limit(1024, 1024**2, 1024*512)
