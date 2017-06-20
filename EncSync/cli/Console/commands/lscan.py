#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...scan import do_scan
from ...common import positive_int
from ...Environment import Environment

def cmd_lscan(console, args):
    parser = argparse.ArgumentParser(description="Scan local directories",
                                     prog=args[0])
    parser.add_argument("dirs", nargs="+")

    ns = parser.parse_args(args[1:])

    env = Environment(console.env)

    return do_scan(env, ["local://" + i for i in ns.dirs])
