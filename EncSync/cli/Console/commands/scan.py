#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...scan import do_scan
from ...common import positive_int, recognize_path
from .... import Paths

def cmd_scan(console, args):
    parser = argparse.ArgumentParser(description="Scan directories",
                                     prog=args[0])
    parser.add_argument("dirs", nargs="+")
    parser.add_argument("--n-workers", default=1, type=positive_int)

    ns = parser.parse_args(args[1:])

    paths = []

    for path in ns.dirs:
        path, path_type = recognize_path(path)

        if path_type == "remote":
            path = "disk://" + Paths.join_properly(console.cwd, path)

        paths.append(path)

    do_scan(paths, ns.n_workers)
