#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

def dir_normalize(path, sep="/"):
    """
        Make `path` end with `sep` if it's not already like that.

        :param path: path to be normalized
        :param sep: separator to use

        :returns: `str`, `path` with `sep` at the end
    """

    return path if path.endswith(sep) else path + sep

def dir_denormalize(path, sep="/"):
    """
        Reverse of `dir_normalize` - remove all `sep` at the end of `path`.

        :param path: path to be denormalized
        :param sep: separator to use

        :returns: `str`, `path` without `sep` at the end
    """

    return path.rstrip(sep)

def contains(container_path, path, sep="/"):
    """
        Check if `path` is inside `container_path`.

        :param container_path: container path
        :param path: path to check
        :param sep: separator to use

        :returns: `bool`
    """

    path = dir_normalize(path, sep)
    container_path = dir_normalize(container_path, sep)

    return path.startswith(container_path) or container_path == path

def join(path1, path2, sep="/"):
    """
        Joins two paths, analagous to `os.path.join()`.
        Passing `None` is equivalent to passing an empty string.

        :param path1: `str` or `None`, first path
        :param path2: `str` or `None`, second path
        :param sep: separator to use

        :returns: `str`
    """

    if path1 is None:
        path1 = ""

    if path2 is None:
        path2 = ""

    path1 = dir_normalize(path1, sep)

    if path2.startswith("/"):
        path2 = path2[1:]

    return path1 + path2

def join_properly(path1, path2, sep="/"):
    """
        Analagous to `join`, except it works like a 'cd' command.

        :param path1: first path
        :param path2: second path
        :param sep: separator to use

        :returns: `str`
    """

    if path2 == "":
        path2 = sep

    if path2.startswith(sep):
        new_path = sep
    else:
        new_path = path1

    for i in path2.split(sep):
        if i == "..":
            new_path = split(new_path, sep)[0]
        elif i in (".", ""):
            continue
        else:
            new_path = join(new_path, i, sep)

    if path2.endswith(sep) and not new_path.endswith(sep):
        new_path += sep

    return new_path

def cut_off(path, suffix, sep="/"):
    """
        Cuts off `suffix` from `path`.

        :param path: path to be cut
        :param suffix: suffix to be cut off
        :param sep: separator to use

        :returns: `str`
    """

    # TODO: Rename this function to cut_suffix

    suffix = dir_normalize(suffix, sep)
    path_n = dir_normalize(path, sep)

    if not path_n.endswith(suffix):
        return path

    idx = path_n.rfind(suffix)

    if idx == -1:
        return path

    return path_n[:idx]

def cut_prefix(path, prefix, sep="/"):
    """
        Cuts off `prefix` from `path`.

        :param path: path to be cut
        :param prefix: prefix to be cut off
        :param sep: separator to use

        :returns: `str`
    """

    prefix = dir_normalize(prefix, sep)
    path_n = dir_normalize(path, sep)

    if path.startswith(prefix):
        return path[len(prefix):]
    elif path_n.startswith(prefix):
        return ""
    else:
        return path

def split(path, sep="/"):
    """
        Split `path` into parent directory and child.
        Separator at the end is ignored.

        :param path: path to be split
        :param sep: separator to use

        :returns: `tuple` of 2 `str` elements
    """

    path = dir_denormalize(path, sep)
    res = path.rsplit(sep, 1)

    if len(res) == 1:
        res.append("")

    return (sep if not res[0] else res[0], res[1])

def to_sys(path, orig_sep="/"):
    """
        Convert `path` to a system path.

        :param path: path to convert
        :param orig_sep: original separator

        :returns: `str`
    """

    return path.replace(orig_sep, os.path.sep)

def path_map(path, f, sep="/"):
    """
        Apply `f` to every path fragment separated by `sep` and then return the resulting path.

        :param path: path to be processed
        :param f: function to be applied
        :param sep: separator to use

        :returns: `str`
    """

    return sep.join(f(i) for i in path.split(sep))

if sys.platform.startswith("win"):
    def from_sys(path, target_sep="/"):
        """
            Convert from system path.

            :param path: path to convert
            :param target_sep: target separator

            :returns: `str`
        """

        path = path.replace(os.path.sep, target_sep)
        path = explicit(path, target_sep)
        return path

    def explicit(path, sep="/"):
        """
            Makes absolute paths start with a drive letter on Windows.
            On other systems it just replaces an empty string with `sep`

            :param path: path to process
            :param sep: separator to use

            :returns: `str`
        """

        if path.startswith(sep) or path == "":
            sys_drive_path = from_sys(os.path.realpath("/"))
            path = join(sys_drive_path, path, sep)

        return path
else:
    def from_sys(path, target_sep="/"):
        """
            Convert from system path.

            :param path: path to convert
            :param target_sep: target separator

            :returns: `str`
        """

        return path.replace(os.path.sep, target_sep)

    def explicit(path, sep="/"):
        """
            Makes absolute paths start with a drive letter on Windows.
            On other systems it just replaces an empty string with `sep`.

            :param path: path to process
            :param sep: separator to use

            :returns: `str`
        """

        return path if path else sep

def from_sys_sep(path, sep="/"):
    """
        Replaces system path separator with `sep`.

        :param path: path to process
        :param sep: separator to use

        :returns: `str`
    """

    return path.replace(os.path.sep, sep)

def sys_explicit(path):
    """
        Same as `explicit(path, os.path.sep)`.

        :param path: path to process

        :returns: `str`
    """

    return explicit(path, os.path.sep)
