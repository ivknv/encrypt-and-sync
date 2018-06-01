#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import unittest

from eas.common import SpeedLimiter

class SpeedLimiterTestCase(unittest.TestCase):
    def _test_limit(self, block_size, limit, block_count=2048):
        quantity = block_size * block_count
        expected_time = quantity / limit
        expected_error = 0.025

        limiter = SpeedLimiter(limit, interval=1.0)

        t1 = time.time()
        limiter.begin()

        for i in range(block_count):
            limiter.quantity += block_size
            limiter.delay()

        t2 = time.time()

        error = abs((t2 - t1) - expected_time) / expected_time

        print("Time: %ss" % (t2 - t1,))
        print("Expected time: %ss" % (expected_time,))
        print("Block size: %s" % (block_size,))
        print("Quantity: %s MiB" % (quantity / 1024**2,))
        print("Speed: %s MiB/s" % (quantity / (t2 - t1) / 1024**2,))
        print("Expected speed: %s MiB/s" % (limit / 1024**2,))
        print("Error: %s%%" % (error * 100.0,))
        print("Expected error: < %s%%" % (expected_error * 100.0,))
        print()

        self.assertLess(error, expected_error)

    def test_limit1(self):
        self._test_limit(4096, 4*1024**2)

    def test_limit2(self):
        self._test_limit(2048, 2*1024**2)

    def test_limit3(self):
        self._test_limit(1024, 1*1024**2)

    def test_limit4(self):
        self._test_limit(512, 0.5*1024**2)

    def test_limit5(self):
        self._test_limit(256, 0.25*1024**2)

    def test_limit6(self):
        self._test_limit(128, 0.125*1024**2)

    def test_limit7(self):
        self._test_limit(2, 1024**2, 2048 * 16 * 32)

    def test_limit8(self):
        self._test_limit(1, 1024**2, 2048 * 16 * 64)
