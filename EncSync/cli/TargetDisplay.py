#!/usr/bin/env python
# -*- coding: utf-8 -*-

import curses
import threading

from . import common

class ScrollableList(object):
    def __init__(self, values=None):
        if values is None:
            values = []

        self.list = values
        self._selection = 0
        self._viewport_idx = 0
        self._viewport_size = 0

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, value):
        self._selection = value % self.length

        d = self._selection - self.viewport_idx

        if d < 0:
            self.viewport_idx = self._selection
        elif d >= self.viewport_size - 1:
            self.viewport_idx = self._selection - self.viewport_size + 1

    @property
    def viewport_idx(self):
        return self._viewport_idx

    @viewport_idx.setter
    def viewport_idx(self, value):
        self._viewport_idx = value % self.length

    @property
    def length(self):
        return len(self.list)

    @property
    def viewport_size(self):
        return min(self._viewport_size, self.length)

    @viewport_size.setter
    def viewport_size(self, value):
        self._viewport_size = value

    @property
    def n_visible(self):
        return min(self.viewport_size, self.length - self.viewport_idx)

class TargetDisplay(object):
    def __init__(self, stdscr=None, target_manager=None):
        self.quit = self.force_quit = False
        self.stdscr = stdscr
        self.targets = []
        self.target_list = ScrollableList(self.targets)
        self.worker_list = ScrollableList()
        self.cur_list = self.target_list
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
            self.cur_list.selection -= 1
        elif k == curses.KEY_DOWN:
            self.cur_list.selection += 1
        elif k in (ord("s"), ord("r")):
            try:
                target = targets[self.target_list.selection]
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
        elif k == ord("\t"):
            if self.cur_list is self.target_list:
                self.cur_list = self.worker_list
            else:
                self.cur_list = self.target_list
        else:
            return

        self.update_screen()

    def handle_key(self, k):
        for handler in self.key_handlers:
            handler(k)

    def getch_waiter(self):
        try:
            while not self.stop_condition():
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
        targets = self.targets
        header = self.target_columns
        rows = []
        colors = [None]

        x = self.x + ox
        y = self.y + oy

        self.target_list.viewport_size = (self.stdscr.getmaxyx()[0] - y - 1) // 2

        a = self.target_list.viewport_idx
        b = a + self.target_list.n_visible

        for i in range(a, b):
            rows.append(self.get_target_columns(targets[i], i))

            if self.cur_list is self.target_list and i == self.target_list.selection:
                colors.append(self.highlight_pair)
            else:
                colors.append(None)

        height = common.display_table(y, x, self.stdscr, header, rows, colors)

        return height

    def display_workers(self, oy=0, ox=0):
        workers = self.target_manager.get_worker_list()

        header = ["No.", "Progress", "Operation", "Path"]
        rows = []
        colors = [None]

        x = self.x + ox
        y = self.y + oy

        height = 1

        self.stdscr.addstr(y, x, "Workers:")

        y += 1

        self.worker_list.list = workers
        self.worker_list.viewport_size = self.stdscr.getmaxyx()[0] - y

        a = self.worker_list.viewport_idx
        b = a + self.worker_list.n_visible

        for i in range(a, b):
            info = workers[i].get_info()
            path = info.get("path", None) or "N/A"
            operation = info.get("operation", None) or "N/A"
            progress = info.get("progress", None) or "N/A"

            operation = operation.capitalize()

            if type(progress) in (int, float):
                progress *= 100.0
                progress = "%.2f%%" % progress

            rows.append([str(i + 1), progress, operation, path])

            if self.cur_list is self.worker_list and i == self.worker_list.selection:
                colors.append(self.highlight_pair)
            else:
                colors.append(None)

        height += common.display_table(y, x, self.stdscr, header, rows, colors)

        return height
