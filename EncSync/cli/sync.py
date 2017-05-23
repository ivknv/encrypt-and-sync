#!/usr/bin/env python
# -*- coding: utf-8 -*-

import curses
import os
import sys
import time

from . import common
from .TargetDisplay import TargetDisplay

from ..Synchronizer import Synchronizer

global_vars = common.global_vars

class SyncTargetDisplay(TargetDisplay):
    def __init__(self, *args, **kwargs):
        TargetDisplay.__init__(self, *args, **kwargs)

        self.target_columns = ["No.", "Progress", "Status", "Stage", "Local", "Remote"]

    def get_target_columns(self, target, idx):
        try:
            progress = target.progress["finished"] / target.total_children * 100.0
        except ZeroDivisionError:
            progress = 100.0 if target.status == "finished" else 0.0

        if self.target_manager.dispatcher.stage is None:
            stage = "None"
        else:
            stage = self.target_manager.dispatcher.stage["name"]

        return [str(idx + 1), "%.2f%%" % progress,
                str(target.status), stage,
                target.local, target.remote]

def do_sync(paths, n_workers):
    encsync, ret = common.make_encsync()

    if encsync is None:
        return ret

    stdscr = curses.initscr()

    try:
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

        curses.noecho()
        curses.cbreak()

        stdscr.keypad(True)

        try:
            ret = _do_sync(stdscr, paths, n_workers)
            curses.endwin()

            return ret
        except ValueError as e:
            curses.endwin()
            print("Error: %s" %e, file=sys.stderr)
            return 1
    except Exception as e:
        curses.endwin()
        raise e

def _do_sync(stdscr, paths, n_workers):
    synchronizer = Synchronizer(global_vars["encsync"], n_workers)

    target_display = SyncTargetDisplay(stdscr, synchronizer)
    target_display.manager_name = "Synchronizer"
    target_display.highlight_pair = curses.color_pair(1)

    for path1, path2 in zip(paths[::2], paths[1::2]):
        path1, path1_type = common.recognize_path(path1)
        path2, path2_type = common.recognize_path(path2)

        if path1_type == path2_type:
            raise ValueError("Expected a pair of both local and remote paths")

        if path1_type == "local":
            local, remote = path1, path2
        else:
            local, remote = path2, path1

        local = os.path.realpath(os.path.expanduser(local))
        remote = common.prepare_remote_path(remote)

        target = synchronizer.add_target(False, local, remote, None)
        target.skip_integrity_check = True

        target_display.targets.append(target)

    target_display.start_getch()

    synchronizer.start()

    while not target_display.stop_condition():
        try:
            target_display.update_screen()
            time.sleep(0.3)
        except KeyboardInterrupt:
            pass

    return 0
