#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

def set_upload_limit(config, args):
    number = parse_size(args[0])

    # Avoid NaN
    if not number >= 0.0:
        raise ValueError("Upload limit must be non-negative")

    config.upload_limit = number

def set_download_limit(config, args):
    number = parse_size(args[0])

    # Avoid NaN
    if not number >= 0.0:
        raise ValueError("Download limit must be non-negative")

    config.download_limit = number
