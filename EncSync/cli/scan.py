#!/usr/bin/env python
# -*- coding: utf-8 -*-

import curses
import time
import os

from ..Scanner import Scanner

from . import common
from .Environment import Environment
from .TargetDisplay import TargetDisplay

class ScanTargetDisplay(TargetDisplay):
    def __init__(self, *args, **kwargs):
        TargetDisplay.__init__(self, *args, **kwargs)
        self.target_columns = ["No.", "Path", "Type", "Status"]

    def get_target_columns(self, target, idx):
        return [str(idx + 1), target.path, target.type, str(target.status)]

def do_scan(env, paths, n_workers):
    encsync, ret = common.make_encsync(env)
    if encsync is None:
        return ret

    stdscr = curses.initscr()
    try:
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        return _do_scan(env, stdscr, paths, n_workers)
    finally:
        curses.endwin()

def _do_scan(env, stdscr, paths, n_workers):
    scanner = Scanner(env["encsync"], n_workers)

    target_display = ScanTargetDisplay(stdscr, scanner)
    target_display.manager_name = "Scanner"
    target_display.highlight_pair = curses.color_pair(1)

    for path in paths:
        path, scan_type = common.recognize_path(path)
        if scan_type == "local":
            path = os.path.realpath(os.path.expanduser(path))
        else:
            path = common.prepare_remote_path(path)

        target_display.targets.append(scanner.add_dir(scan_type, path))

    scanner.start()

    getch_thread = target_display.start_getch()

    while not target_display.stop_condition():
        try:
            target_display.update_screen()
            time.sleep(0.3)
        except KeyboardInterrupt:
            pass

    if getch_thread.is_alive():
        target_display.stdscr.clear()
        target_display.stdscr.addstr(0, 0, "Press enter to quit")
        target_display.stdscr.refresh()

    getch_thread.join()

    return 0
