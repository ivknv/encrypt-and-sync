#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

def dir_normalize(path, sep="/"):
    return path if path.endswith(sep) else path + sep

def dir_denormalize(path, sep="/"):
    while path.endswith(sep):
        path = path[:-1]
    return path

def contains(container, path, sep="/"):
    container = dir_normalize(container, sep)

    return path.startswith(container) or path == container[:-1]

def join(path1, path2, sep="/"):
    if path1 is None:
        path1 = ""

    if path2 is None:
        path2 = ""

    path1 = dir_normalize(path1, sep)

    if path2.startswith("/"):
        path2 = path2[1:]

    return path1 + path2

def join_properly(path1, path2, sep="/"):
    if path2.startswith(sep):
        new_path = sep
    else:
        new_path = path1

    for i in path2.split(sep):
        if i == "..":
            new_path = split(new_path)[0]
        elif i in (".", ""):
            continue
        else:
            new_path = join(new_path, i)

    if path2.endswith(sep):
        new_path += sep

    return new_path

def cut_off(path, prefix, sep="/"):
    prefix = dir_normalize(prefix, sep)
    path_n = dir_normalize(path, sep)

    if not path_n.endswith(prefix):
        return path

    idx = path_n.rfind(prefix)

    if idx == -1:
        return path

    return path_n[:idx]

def cut_prefix(path, prefix, sep="/"):
    prefix = dir_normalize(prefix, sep)
    path_n = dir_normalize(path, sep)

    if path.startswith(prefix):
        return path[len(prefix):]
    elif path_n.startswith(prefix):
        return ""
    else:
        return path

def split(path, sep="/"):
    normalize = path.endswith(sep)
    path = dir_denormalize(path, sep)
    res = path.rsplit(sep, 1)

    if len(res) == 1:
        res.append("")

    if res[1] != "" and normalize:
        res[1] = dir_normalize(res[1], sep)

    return (sep if not res[0] else res[0], res[1])

def from_sys(path, target_sep="/"):
    return path.replace(os.path.sep, target_sep)

def to_sys(path, orig_sep="/"):
    return path.replace(orig_sep, os.path.sep)

def path_map(path, f, sep="/"):
    return sep.join(f(i) for i in path.split(sep))
