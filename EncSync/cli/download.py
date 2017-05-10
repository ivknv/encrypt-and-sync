#!/usr/bin/env python
# -*- coding: utf-8 -*-

import curses
import os
import time

from ..Downloader import Downloader

from .TargetDisplay import TargetDisplay

from . import common

global_vars = common.global_vars

class DownloadTargetDisplay(TargetDisplay):
    def __init__(self, *args, **kwargs):
        TargetDisplay.__init__(self, *args, **kwargs)
        self.target_columns = ["No.", "Progress", "Status", "Source", "Destination"]

    def get_target_columns(self, target, idx):
        try:
            progress = target.progress["finished"] / target.total_children
            progress *= 100.0
        except ZeroDivisionError:
            progress = 100.0 if target.status == "finished" else 0.0

        return [str(idx + 1),
                "%.2f%%" % progress,
                str(target.status),
                str(target.dec_remote),
                str(target.local)]

def download(paths):
    common.make_encsync()

    stdscr = curses.initscr()
    try:
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        _download(stdscr, paths)
    finally:
        curses.endwin()

def _download(stdscr, paths):
    downloader = Downloader(global_vars["encsync"], global_vars["n_workers"])

    target_display = DownloadTargetDisplay(stdscr, downloader)
    target_display.highlight_pair = curses.color_pair(1)
    target_display.manager_name = "Downloader"

    if global_vars.get("remote_prefix", None) is None:
        raise ValueError("--remote-prefix must be specified")

    if len(paths) == 1:
        local = os.getcwd()
    else:
        local = paths.pop()

    for path in paths:
        path, path_type = common.recognize_path(path)

        target = downloader.add_download(global_vars["remote_prefix"], path, local)
        target_display.targets.append(target)

    downloader.start()

    target_display.start_getch()

    while not target_display.stop_condition():
        try:
            target_display.update_screen()
            time.sleep(0.3)
        except KeyboardInterrupt:
            pass
