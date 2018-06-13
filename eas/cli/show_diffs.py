#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import os

from .common import show_error, make_config
from ..common import validate_folder_name, recognize_path
from ..file_comparator import compare_lists
from .. import pathm
from .pager import Pager

__all__ = ["show_diffs"]

@functools.lru_cache(maxsize=1024)
def _get_diff_dst_subpath(config, dst_path):
    dst_path, dst_path_type = recognize_path(dst_path)

    dst_folder = config.identify_folder(dst_path_type, dst_path)

    if dst_folder is None:
        dst_subpath = "/"
    else:
        dst_subpath = pathm.cut_prefix(dst_path, dst_folder["path"])
        dst_subpath = pathm.join("/", dst_subpath)

    return dst_subpath

def get_diff_dst_subpath(config, diff):
    return _get_diff_dst_subpath(config, diff["dst_path"])

def format_diff(config, diff):
    dst_path = recognize_path(diff["dst_path"])[0]
    dst_subpath = get_diff_dst_subpath(config, diff)

    dst_path = pathm.join(dst_subpath, diff["path"])
    dst_path = dst_path.lstrip("/") or "/"

    return "%s %s %s\n" % (diff["type"], diff["node_type"], dst_path)

def write_diff(file_obj, diff):
    file_obj.write(format_diff)

def show_diffs(env, src_name_or_path, dst_name_or_path):
    config, ret = make_config(env, load_encrypted_data=False)

    if config is None:
        return ret

    if validate_folder_name(src_name_or_path):
        try:
            folder = config.folders[src_name_or_path]
            src_path = folder["type"] + "://" + folder["path"]
        except KeyError:
            show_error("Error: unknown folder %r" % (dst_name_or_path,))
    else:
        src_path, src_path_type = recognize_path(src_name_or_path)

        if src_path_type == "local":
            src_path = pathm.from_sys(os.path.abspath(os.path.expanduser(src_path)))

        src_path = src_path_type + "://" + src_path

    if validate_folder_name(dst_name_or_path):
        try:
            folder = config.folders[dst_name_or_path]
            dst_path = folder["type"] + "://" + folder["path"]
        except KeyError:
            show_error("Error: unknown folder %r" % (dst_name_or_path,))
    else:
        dst_path, dst_path_type = recognize_path(dst_name_or_path)

        if dst_path_type == "local":
            dst_path = pathm.from_sys(os.path.abspath(os.path.expanduser(dst_path)))

        dst_path = dst_path_type + "://" + dst_path

    diff_buf = []

    it = iter(compare_lists(config, src_path, dst_path, env["db_dir"]))

    for i in range(50):
        try:
            diff = next(it)
        except StopIteration:
            break

        diff_buf.append(diff)

    pager = Pager()
    out_file = None

    if len(diff_buf) < 50:
        pager.command = None

    for diff in diff_buf:
        pager.stdin.write(format_diff(config, diff))

    del diff_buf

    for diff in it:
        pager.stdin.write(format_diff(config, diff))

    pager.run()

    return 0
