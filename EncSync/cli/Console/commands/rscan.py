#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...scan import do_scan
from ...common import positive_int
from ...Environment import Environment
from .... import Paths

def cmd_rscan(console, args):
    parser = argparse.ArgumentParser(description="Scan remote directories",
                                     prog=args[0])
    parser.add_argument("dirs", nargs="+")
    parser.add_argument("--n-workers", "-w", type=positive_int)

    ns = parser.parse_args(args[1:])

    paths = ["disk://" + Paths.join_properly(console.cwd, i) for i in ns.dirs]

    env = Environment(console.env)

    if ns.n_workers is not None:
        env["n_workers"] = ns.n_workers

    return do_scan(env, paths)
