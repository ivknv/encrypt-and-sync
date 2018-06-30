# -*- coding: utf-8 -*-

from datetime import datetime
import os
import sys
import threading

from .. import pathm

from .lazy_dict import *
from .lockfile import *
from .lru_cache import *
from .speed_limiter import *

__all__ = ["node_tuple_to_dict", "normalize_node", "escape_glob",
           "validate_folder_name", "is_windows", "get_file_size", "parse_size",
           "DummyException", "recognize_path", "threadsafe_iterator",
           "ThreadsafeIterator", "LazyDict", "Lockfile", "LRUCache", "SpeedLimiter"]

class DummyException(Exception):
    """Should not be raised anywhere."""

    pass

def node_tuple_to_dict(t):
    if t is not None:
        return {"type": t[0],
                "modified": t[1] / 1e6,
                "padded_size": t[2],
                "mode": t[3],
                "owner": t[4],
                "group": t[5],
                "path": t[6],
                "link_path": t[7],
                "IVs": t[8]}

    return {"type": None,
            "modified": None,
            "padded_size": None,
            "mode": None,
            "owner": None,
            "group": None,
            "path": None,
            "link_path": None,
            "IVs": None}

def normalize_node(node):
    if node["type"] == "d":
        node["path"] = pathm.dir_normalize(node["path"])

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

class ThreadsafeIterator(object):
    def __init__(self, it, lock_factory=threading.Lock):
        self.lock = lock_factory()
        self.it = it

    def __iter__(self):
        return self

    def __next__(self):
        with self.lock:
            return next(self.it)

def threadsafe_iterator(f):
    def decorated(*args, **kwargs):
        return ThreadsafeIterator(f(*args, **kwargs))

    return decorated
