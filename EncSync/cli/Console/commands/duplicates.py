#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...show_duplicates import show_duplicates
from ...common import recognize_path, non_local_path
from .... import Paths

def cmd_duplicates(console, args):
    parser = argparse.ArgumentParser(description="Show duplicates",
                                     prog=args[0])
    parser.add_argument("dirs", nargs="+", type=non_local_path)

    ns = parser.parse_args(args[1:])

    paths = []

    for path in ns.dirs:
        path, path_type = recognize_path(path)

        path = Paths.join_properly(console.cwd, path)

        paths.append(path)

    return show_duplicates(paths)
