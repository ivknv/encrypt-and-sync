#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from . import Paths

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime(DATE_FORMAT)

def parse_timestamp(s):
    return datetime.strptime(s, DATE_FORMAT).timestamp()

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

def normalize_node(node, local=True):
    if local:
        node["path"] = Paths.from_sys(node["path"])
    if node["type"] == "d":
        node["path"] = Paths.dir_normalize(node["path"])
