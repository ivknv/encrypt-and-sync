#!/usr/bin/env python
# -*- coding: utf-8 -*-

import curses

from . import ScrollableList
from .. import common

class TargetList(ScrollableList):
    def __init__(self, target_manager, targets=None, root=None):
        if targets is None:
            targets = []

        self.targets = targets
        self.target_manager = target_manager

        ScrollableList.__init__(self, self.targets, root)

        self.columns = ["No.", "Path", "Status"]

        self.highlight_pair = None

        self.get_target_columns = self.default_get_target_columns

        self.add_key_handler((curses.KEY_UP, curses.KEY_DOWN), self.handle_arrows)
        self.add_key_handler((ord("s"),), self.handle_suspend)
        self.add_key_handler((ord("r"),), self.handle_resume)

    def handle_arrows(self, k):
        if k == curses.KEY_UP:
            self.selection -= 1
        elif k == curses.KEY_DOWN:
            self.selection += 1

    def handle_suspend(self, k):
        target = self.list[self.selection]

        if target.status not in ("finished", "failed"):
            target.change_status("suspended")

    def handle_resume(self, k):
        target = self.list[self.selection]

        if target.status == "suspended":
            target.change_status("pending")

        if target not in self.target_manager.get_targets():
            self.target_manager.add_target(target)

        self.target_manager.start_if_not_alive()

    def default_get_target_columns(self, target, idx):
        return [str(idx + 1), target.path, str(target.status)]

    def display(self, window, ox=0, oy=0):
        rows = []
        colors = [None]

        x = self.x + ox
        y = self.y + oy

        self.viewport_size = (window.getmaxyx()[0] - y) // 2

        a = self.viewport_idx
        b = a + self.n_visible

        for i in range(a, b):
            rows.append(self.get_target_columns(self.targets[i], i))

            if i == self.selection and self.focused:
                colors.append(self.highlight_pair)
            else:
                colors.append(None)

        height = common.display_table(y, x, window, self.columns, rows, colors) + 1

        return height
