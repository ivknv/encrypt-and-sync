#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...show_diffs import show_diffs
from ...common import recognize_path, local_path, non_local_path
from .... import Paths

def cmd_diffs(console, args):
    parser = argparse.ArgumentParser(description="Show differences",
                                     prog=args[0])
    parser.add_argument("local", type=local_path)
    parser.add_argument("remote", type=non_local_path)

    ns = parser.parse_args(args[1:])

    ns.local = recognize_path(ns.local)[0]
    ns.remote = Paths.join_properly(console.cwd, recognize_path(ns.remote)[0])

    return show_diffs(ns.local, ns.remote)
