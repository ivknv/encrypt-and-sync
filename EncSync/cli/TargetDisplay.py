#!/usr/bin/env python
# -*- coding: utf-8 -*-

import curses
import threading

from . import common

class TargetDisplay(object):
    def __init__(self, stdscr=None, target_manager=None):
        self.quit = self.force_quit = False
        self.cur_target_idx = 0
        self.stdscr = stdscr
        self.targets = []
        self.target_manager = target_manager
        self.manager_name = "<Target manager>"
        self.x = self.y = 0
        self.highlight_pair = None

        self.target_columns = ["No.", "Path", "Status"]

        self.key_handlers = [self.main_key_handler]

        self.strings = {}

    def stop_condition(self):
        return (self.quit and not self.target_manager.is_alive()) or self.force_quit

    def update_screen(self):
        self.stdscr.clear()
        self.display_info()
        for string in self.strings.values():
            y, x, s, color_pair = string
            if color_pair is not None:
                self.stdscr.addstr(y, x, s, color_pair)
            else:
                self.stdscr.addstr(y, x, s)

        self.stdscr.refresh()

    def main_key_handler(self, k):
        targets = self.targets

        if k == curses.KEY_UP:
            if self.cur_target_idx == 0:
                self.cur_target_idx = len(targets) - 1
            else:
                self.cur_target_idx -= 1
        elif k == curses.KEY_DOWN:
            if self.cur_target_idx >= len(targets) - 1:
                self.cur_target_idx = 0
            else:
                self.cur_target_idx += 1
        elif k in (ord("s"), ord("r")):
            try:
                target = targets[min(self.cur_target_idx, len(targets) - 1)]
                if target.status != "finished":
                    if k == ord("s"):
                        target.change_status("suspended")
                    elif target.status == "suspended":
                        target.change_status("pending")
                        if target not in self.target_manager.get_targets():
                            self.target_manager.add_target(target)
                        self.target_manager.start_if_not_alive()
            except IndexError:
                pass
        elif k in (ord("S"), ord("q")):
            self.target_manager.stop()
            for target in targets:
                if target.status != "finished":
                    target.change_status("suspended")

            if k == ord("q"):
                self.quit = True
        elif k == ord("Q"):
            self.quit = True
            self.force_quit = True

        if k != -1:
            self.update_screen()

    def handle_key(self, k):
        for handler in self.key_handlers:
            handler(k)

    def getch_waiter(self):
        try:
            while (not self.quit or self.target_manager.is_alive()) and not self.force_quit:
                k = self.stdscr.getch()

                self.handle_key(k)
        finally:
            self.quit = True
            self.force_quit = True

    def start_getch(self, daemon=True):
        thread = threading.Thread(target=self.getch_waiter, daemon=daemon)
        thread.start()
        return thread

    def display_info(self, oy=0, ox=0):
        height = self.display_manager_info(oy, ox)

        height += 1

        height += self.display_target_info(oy + height, ox)

        height += 1

        height += self.display_workers(oy + height, ox)

        return height

    def display_manager_info(self, oy=0, ox=0):
        x = self.x + ox
        y = self.y + oy

        if self.target_manager.is_alive():
            if self.target_manager.stopped:
                self.stdscr.addstr(y, x, "%s is shutting down" % self.manager_name)
            else:
                self.stdscr.addstr(y, x, "%s is running" % self.manager_name)
        else:
            self.stdscr.addstr(y, x, "%s is not running" % self.manager_name)

        height = 1

        return height

    def get_target_columns(self, target, idx):
        return [str(idx + 1), target.path, str(target.status)]

    def display_target_info(self, oy=0, ox=0):
        header = self.target_columns
        rows = []
        colors = [None]

        x = self.x + ox
        y = self.y + oy

        targets = self.targets

        for target, i in zip(targets, range(len(targets))):
            rows.append(self.get_target_columns(target, i))

            colors.append(self.highlight_pair if i == self.cur_target_idx else None)

        height = common.display_table(y, x, self.stdscr, header, rows, colors)

        return height

    def display_workers(self, oy=0, ox=0):
        workers = self.target_manager.get_worker_list()

        header = ["No.", "Progress", "Operation", "Path"]
        rows = []

        x = self.x + ox
        y = self.y + oy

        height = 1

        self.stdscr.addstr(y, x, "Workers:")

        y += 1

        for worker, i in zip(workers, range(len(workers))):
            info = worker.get_info()
            path = info.get("path", None) or "N/A"
            operation = info.get("operation", None) or "N/A"
            progress = info.get("progress", None) or "N/A"

            operation = operation.capitalize()

            if type(progress) in (int, float):
                progress *= 100.0
                progress = "%.2f%%" % progress

            rows.append([str(i + 1), progress, operation, path])

        height += common.display_table(y, x, self.stdscr, header, rows)

        return height
