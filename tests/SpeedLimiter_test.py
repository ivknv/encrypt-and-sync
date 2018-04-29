#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import unittest

from eas.SpeedLimiter import SpeedLimiter

class SpeedLimiterTestCase(unittest.TestCase):
    def test_limit(self):
        block_size = 4096
        block_count = 2048
        quantity = block_size * block_count
        limit = 1.5 * 1024**2
        expected_time = quantity / limit
        expected_error = 0.025

        limiter = SpeedLimiter(limit, interval=1.0)

        t1 = time.time()
        limiter.begin()

        for i in range(block_count):
            limiter.delay()
            limiter.quantity += block_size

        t2 = time.time()

        error = abs((t2 - t1) - expected_time) / expected_time

        print("Time: %s" % (t2 - t1,))
        print("Expected time: %s" % (expected_time,))
        print("Quantity: %s" % (quantity,))
        print("Speed: %s * 10**6" % (quantity / (t2 - t1) / 10**6,))
        print("Expected speed: %s * 10**6" % (limit / 10**6,))
        print("Error: %s%%" % (error * 100.0,))
        print("Expected error: < %s%%" % (expected_error * 100.0,))

        self.assertLess(error, expected_error)
