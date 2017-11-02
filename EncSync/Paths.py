#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import reduce

import os
import sys

def get_default_sep(preferred_type):
    if issubclass(preferred_type, str):
        return preferred_type("/")
    elif issubclass(preferred_type, bytes):
        return preferred_type(b"/")

    raise TypeError("Invalid path type: %r instead of str or bytes" % (preferred_type,))

def get_preferred_type(values):
    NoneType = type(None)

    def func(x, y):
        if x is y or y is NoneType:
            return x

        if x is NoneType:
            return y

        raise TypeError("Mixing %r and %r is not allowed" % (x, y))

    preferred_type = reduce(func, [type(v) for v in values])

    if preferred_type is NoneType:
        return str

    return preferred_type

def dir_normalize(path, sep=None):
    """
        Make `path` end with `sep` if it's not already like that.

        :param path: path to be normalized
        :param sep: separator to use

        :returns: `str` or `bytes`, `path` with `sep` at the end
    """

    preferred_type = get_preferred_type([path, sep])

    if sep is None:
        sep = get_default_sep(preferred_type)

    if path is None:
        return sep

    return path if path.endswith(sep) else path + sep

def dir_denormalize(path, sep=None):
    """
        Reverse of `dir_normalize` - remove all `sep` at the end of `path`.

        :param path: path to be denormalized
        :param sep: separator to use

        :returns: `str` or `bytes`, `path` without `sep` at the end
    """

    preferred_type = get_preferred_type([path, sep])

    if sep is None:
        sep = get_default_sep(preferred_type)

    return path.rstrip(sep)

def contains(container_path, path, sep=None):
    """
        Check if `path` is inside `container_path`.

        :param container_path: container path
        :param path: path to check
        :param sep: separator to use

        :returns: `bool`
    """

    preferred_type = get_preferred_type([container_path, path, sep])

    if sep is None:
        sep = get_default_sep(preferred_type)

    if container_path is None:
        container_path = preferred_type()

    if path is None:
        path = preferred_type()

    path = dir_normalize(path, sep)
    container_path = dir_normalize(container_path, sep)

    return path.startswith(container_path) or container_path == path

def join(*paths, sep=None):
    """
        Joins two paths, analagous to `os.path.join()`.
        Passing `None` is equivalent to passing an empty string.

        :param paths: `str`, `bytes`, or `None`, paths to join
        :param sep: separator to use

        :returns: `str` or `bytes`, depending on input
    """

    if len(paths) < 2:
        raise TypeError("Expected at least 2 paths (%d given)" % (len(paths),))

    preferred_type = get_preferred_type(paths + (sep,))

    if sep is None:
        sep = get_default_sep(preferred_type)

    paths = tuple(preferred_type() if not path else path for path in paths)

    new_paths = [paths[0].rstrip(sep)]
    new_paths.extend(path for path in (path.strip(sep) for path in paths[1:-1]) if path)
    new_paths.append(paths[-1].lstrip(sep))

    return sep.join(new_paths)

def join_properly(*paths, sep=None):
    """
        Analogous to `join`, except it works like a 'cd' command.

        :param paths: `str`, `bytes` or `None`, paths to join
        :param sep: separator to use

        :returns: `str` or `bytes`, depending on input
    """

    if len(paths) < 2:
        raise TypeError("Expected at least 2 paths (%d given)" % (len(paths),))

    preferred_type = get_preferred_type(paths + (sep,))

    if sep is None:
        sep = get_default_sep(preferred_type)

    def func(x, y):
        if x is None:
            x = preferred_type()

        if y is None:
            y = preferred_type()

        if y in (".", b".") or not y:
            return x

        if y in ("..", b".."):
            return split(x, sep)[0]

        return join(x, y, sep=sep)

    result = paths[0]

    if not result:
        result = sep

    for path in paths[1:]:
        if path.startswith(sep) or not path:
            result = sep

        result = reduce(func, [result] + path.split(sep))

        if path.endswith(sep):
            result = dir_normalize(result, sep)

    return result

def cut_off(path, suffix, sep=None):
    """
        Cuts off `suffix` from `path`.

        :param path: path to be cut
        :param suffix: suffix to be cut off
        :param sep: separator to use

        :returns: `str` or `bytes`
    """

    # TODO: Rename this function to cut_suffix

    preferred_type = get_preferred_type([path, suffix, sep])

    if sep is None:
        sep = get_default_sep(preferred_type)

    if path is None:
        path = preferred_type()

    if suffix is None:
        suffix = preferred_type()

    suffix = dir_normalize(suffix, sep)
    path_n = dir_normalize(path, sep)

    if not path_n.endswith(suffix):
        return path

    idx = path_n.rfind(suffix)

    if idx == -1:
        return path

    return path_n[:idx]

def cut_prefix(path, prefix, sep=None):
    """
        Cuts off `prefix` from `path`.

        :param path: path to be cut
        :param prefix: prefix to be cut off
        :param sep: separator to use

        :returns: `str` or `bytes`
    """

    preferred_type = get_preferred_type([path, prefix, sep])

    if sep is None:
        sep = get_default_sep(preferred_type)

    if prefix is None:
        prefix = preferred_type()

    if path is None:
        path = preferred_type()

    prefix = dir_normalize(prefix, sep)
    path_n = dir_normalize(path, sep)

    if path.startswith(prefix):
        return path[len(prefix):]
    elif path_n.startswith(prefix):
        return preferred_type()
    else:
        return path

def split(path, sep=None):
    """
        Split `path` into parent directory and child.
        Separator at the end is ignored.

        :param path: path to be split
        :param sep: separator to use

        :returns: `tuple` of 2 `str` or `bytes` elements
    """

    preferred_type = get_preferred_type([path, sep])

    if sep is None:
        sep = get_default_sep(preferred_type)

    if path is None:
        path = preferred_type()

    path = dir_denormalize(path, sep)
    res = path.rsplit(sep, 1)

    if len(res) == 1:
        res.append("")

    return (sep if not res[0] else res[0], res[1])

def to_sys(path, orig_sep=None):
    """
        Convert `path` to a system path.

        :param path: path to convert
        :param orig_sep: original separator

        :returns: `str` or `bytes`
    """

    preferred_type = get_preferred_type([path, orig_sep])

    if orig_sep is None:
        orig_sep = get_default_sep(preferred_type)

    if path is None:
        path = preferred_type()

    sys_sep = os.path.sep

    if isinstance(path, bytes):
        sys_sep = sys_sep.encode()

    return path.replace(orig_sep, sys_sep)

def path_map(path, f, sep=None):
    """
        Apply `f` to every path fragment separated by `sep` and then return the resulting path.

        :param path: path to be processed
        :param f: function to be applied
        :param sep: separator to use

        :returns: `str` or `bytes`
    """

    preferred_type = get_preferred_type([path, sep])

    if sep is None:
        sep = get_default_sep(preferred_type)

    if path is None:
        path = preferred_type()

    return join(*tuple(f(i) for i in path.split(sep)), sep=sep)

if sys.platform.startswith("win"):
    def from_sys(path, target_sep=None):
        """
            Convert from system path.

            :param path: path to convert
            :param target_sep: target separator

            :returns: `str` or `bytes`
        """

        preferred_type = get_preferred_type([path, target_sep])

        if target_sep is None:
            target_sep = get_default_sep(preferred_type)

        if path is None:
            path = preferred_type()

        sys_sep = os.path.sep

        if issubclass(preferred_type, bytes):
            sys_sep = sys_sep.encode("utf8")

        path = path.replace(sys_sep, target_sep)
        path = explicit(path, target_sep)

        return path

    def explicit(path, sep=None):
        """
            Makes absolute paths start with a drive letter on Windows.
            On other systems it just replaces an empty string with `sep`

            :param path: path to process
            :param sep: separator to use

            :returns: `str` or `bytes`
        """

        preferred_type = get_preferred_type([path, sep])

        if sep is None:
            sep = get_default_sep(preferred_type)

        if path is None:
            path = preferred_type()

        if path.startswith(sep) or not path:
            root = "/"
            if issubclass(preferred_type, bytes):
                root = root.encode()

            sys_drive_path = from_sys(os.path.realpath(root))
            path = join(sys_drive_path, path, sep=sep)

        return path
else:
    def from_sys(path, target_sep=None):
        """
            Convert from system path.

            :param path: path to convert
            :param target_sep: target separator

            :returns: `str` or `bytes`
        """

        preferred_type = get_preferred_type([path, target_sep])

        if target_sep is None:
            target_sep = get_default_sep(preferred_type)

        if path is None:
            path = preferred_type()

        sys_sep = os.path.sep

        if issubclass(preferred_type, bytes):
            sys_sep = sys_sep.encode()

        return path.replace(sys_sep, target_sep)

    def explicit(path, sep=None):
        """
            Makes absolute paths start with a drive letter on Windows.
            On other systems it just replaces an empty string with `sep`.

            :param path: path to process
            :param sep: separator to use

            :returns: `str` or `bytes`
        """

        preferred_type = get_preferred_type([path, sep])

        if sep is None:
            sep = get_default_sep(preferred_type)

        if path is None:
            path = preferred_type()

        return path if path else sep

def from_sys_sep(path, sep=None):
    """
        Replaces system path separator with `sep`.

        :param path: path to process
        :param sep: separator to use

        :returns: `str` or `bytes`
    """

    preferred_type = get_preferred_type([path, sep])

    if sep is None:
        sep = get_default_sep(preferred_type)

    if path is None:
        path = preferred_type()

    sys_sep = os.path.sep

    if issubclass(preferred_type, bytes):
        sys_sep = sys_sep.encode()

    return path.replace(sys_sep, sep)

def sys_explicit(path):
    """
        Same as `explicit(path, os.path.sep)`.

        :param path: path to process

        :returns: `str` or `bytes`
    """

    sys_sep = os.path.sep

    if isinstance(path, bytes):
        sys_sep = sys_sep.encode()

    return explicit(path, sys_sep)
