#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from .... import Paths
from ...download import download
from ...common import positive_int
from ...Environment import Environment

def cmd_download(console, args):
    parser = argparse.ArgumentParser(description="Download file from Yandex Disk",
                                     prog=args[0])
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--n-workers", "-w", default=1, type=positive_int)

    ns = parser.parse_args(args[1:])

    if len(ns.paths) > 1:
        paths = [Paths.join_properly(console.cwd, i) for i in ns.paths[:-1]]
        paths.append(ns.paths[-1])
    else:
        paths = [Paths.join_properly(console.cwd, ns.paths[0])]

    env = Environment(console.env)

    return download(env, paths, ns.n_workers)
