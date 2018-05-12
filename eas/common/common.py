#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import os
import sys

from .. import Paths

__all__ = ["format_timestamp", "parse_timestamp", "node_tuple_to_dict",
           "normalize_node", "escape_glob", "validate_folder_name",
           "is_windows", "get_file_size", "parse_size", "recognize_path",
           "DummyException"]

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class DummyException(Exception):
    """Should not be raised anywhere."""

    pass

def format_timestamp(timestamp):
    try:
        return datetime.fromtimestamp(timestamp).strftime(DATE_FORMAT)
    except OSError:
        return datetime.fromtimestamp(86400).strftime(DATE_FORMAT)

def parse_timestamp(s):
    try:
        return datetime.strptime(s, DATE_FORMAT).timestamp()
    except OSError:
        return 86400

def node_tuple_to_dict(t):
    if t is not None:
        return {"type": t[0],
                "modified": parse_timestamp(t[1]),
                "padded_size": t[2],
                "path": t[3],
                "IVs": t[4] if len(t) >= 5 else b""}

    return {"type": None,
            "modified": None,
            "padded_size": None,
            "path": None,
            "IVs": None}

def normalize_node(node):
    if node["type"] == "d":
        node["path"] = Paths.dir_normalize(node["path"])

def escape_glob(s):
    return "".join("[" + i + "]" if i in "*?[]" else i for i in s)

def validate_folder_name(name):
    return all(c.isalnum() or c in "_-+." for c in name)

def is_windows():
    return sys.platform.startswith("win")

def get_file_size(file_or_path):
    if isinstance(file_or_path, (str, bytes)):
        return os.path.getsize(file_or_path)

    fpos = file_or_path.tell()

    file_or_path.seek(0, 2)
    size = file_or_path.tell()
    file_or_path.seek(fpos)

    return size

def recognize_path(path, default="local"):
    before, div, after = path.partition("://")

    if not div:
        return (before, default)

    sub_map = {"disk": "yadisk"}

    before = sub_map.get(before, before)

    return (after, before)

def parse_size(s):
    if s.lower() in ("inf", "nan"):
        return float(s)

    try:
        last = s[-1].lower()

        try:
            if last.isdigit():
                return float(s)
        except ValueError:
            raise ValueError("Expected a non-negative number")
    except IndexError:
        return 0

    powers = {"k": 1, "m": 2, "g": 3, "t": 4}

    try:
        power = powers[last]
    except KeyError:
        raise ValueError("Unknown size suffix: %r" % last)

    try:
        return float(s[:-1]) * 1024 ** power
    except ValueError:
        raise ValueError("Expected a non-negative number")
