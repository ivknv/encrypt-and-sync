#!/usr/bin/env python
# -*- coding: utf-8 -*-

import curses
import os
import time

from ..Downloader import Downloader

from .Elements import TargetDisplay

from . import common

class DownloadTargetDisplay(TargetDisplay):
    def __init__(self, *args, **kwargs):
        TargetDisplay.__init__(self, *args, **kwargs)
        self.target_list.columns = ["No.", "Progress", "Status", "Source", "Destination"]
        self.target_list.get_target_columns = self.get_target_columns

        self.manager_name = "Downloader"

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

def download(env, paths, n_workers):
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
        try:
            ret = _download(env, stdscr, paths, n_workers)
            curses.endwin()

            return ret
        except ValueError as e:
            curses.endwin()
            print("Error: %s" %e)
            return 1
    except Exception as e:
        curses.endwin()
        raise e

def _download(env, stdscr, paths, n_workers):
    encsync = env["encsync"]

    downloader = Downloader(encsync, n_workers)

    target_display = DownloadTargetDisplay(downloader)
    target_display.highlight_pair = curses.color_pair(1)

    if len(paths) == 1:
        local = os.getcwd()
    else:
        local = paths.pop()

    for path in paths:
        path, path_type = common.recognize_path(path)

        path = common.prepare_remote_path(path)

        prefix = encsync.find_encrypted_dir(path)

        if prefix is None:
            raise ValueError("%r does not appear to be encrypted" % path)

        target = downloader.add_download(prefix, path, local)
        target_display.targets.append(target)

    downloader.start()

    getch_thread = target_display.start_getch(stdscr)

    while not target_display.stop_condition():
        try:
            target_display.update_screen(stdscr)
            time.sleep(0.3)
        except KeyboardInterrupt:
            pass

    if getch_thread.is_alive():
        stdscr.clear()
        stdscr.addstr(0, 0, "Press enter to quit")
        stdscr.refresh()

    getch_thread.join()

    return 0
