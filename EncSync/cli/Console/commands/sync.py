#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...sync import do_sync
from ...common import positive_int, recognize_path
from ...Environment import Environment
from .... import Paths

def cmd_sync(console, args):
    parser = argparse.ArgumentParser(description="Sync directories",
                                     prog=args[0])
    parser.add_argument("dirs", nargs="*")
    parser.add_argument("-a", "--all", default=False, action="store_true")
    parser.add_argument("--n-workers", "-w", type=positive_int)
    parser.add_argument("--ask", default=False, action="store_true")
    parser.add_argument("--no-scan", default=False, action="store_true")
    parser.add_argument("--no-check", default=False, action="store_true")
    parser.add_argument("--no-choice", default=False, action="store_true")
    parser.add_argument("--no-diffs", default=False, action="store_true")

    ns = parser.parse_args(args[1:])

    paths = []

    for path in ns.dirs:
        path, path_type = recognize_path(path)

        if path_type == "remote":
            path = "disk://" + Paths.join_properly(console.cwd, path)

        paths.append(path)

    env = Environment(console.env)
    env["all"] = ns.all
    env["ask"] = ns.ask
    env["no_check"] = ns.no_check
    env["no_scan"] = ns.no_scan
    env["no_diffs"] = ns.no_diffs
    env["no_choice"] = ns.no_choice

    if ns.n_workers is not None:
        env["n_workers"] = ns.n_workers

    return do_sync(env, paths)
