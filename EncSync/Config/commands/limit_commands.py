#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Command import Command

def parse_size(s):
    if s.lower() in ("inf", "nan"):
        return float(s)

    try:
        last = s[-1].lower()

        if last.isdigit():
            return float(s)
        else:
            size = float(s[:-1])
    except IndexError:
        return 0

    powers = {"k": 1, "m": 2, "g": 3}

    try:
        return size * 1024 ** powers[last]
    except KeyError:
        raise ValueError("Unknown suffix: %r" % last)

class UploadLimitCommand(Command):
    def evaluate(self, config):
        limit = parse_size(self.args[1])

        if not limit >= 0.0:
            raise ValueError("Expected a non-negative number")

        config.upload_limit = limit

class DownloadLimitCommand(Command):
    def evaluate(self, config):
        limit = parse_size(self.args[1])

        if not limit >= 0.0:
            raise ValueError("Expected a non-negative number")

        config.download_limit = limit
