#!/usr/bin/env python
# -*- coding: utf-8 -*-

import curses

from . import ScrollableList
from .. import common

class WorkerList(ScrollableList):
    def __init__(self, worker_owner=None, root=None):
        ScrollableList.__init__(self, None, root)

        self.worker_owner = worker_owner

        self.highlight_pair = None

        self.columns = ["No.", "%", "Operation", "Path"]

        self.add_key_handler((curses.KEY_UP, curses.KEY_DOWN), self.handle_arrows)

    def handle_arrows(self, k):
        if k == curses.KEY_UP:
            self.selection -= 1
        elif k == curses.KEY_DOWN:
            self.selection += 1

    def get_worker_columns(self, worker, idx):
        info = worker.get_info()

        path = info.get("path", None) or "N/A"
        operation = info.get("operation", None) or "N/A"
        operation = operation.capitalize()
        progress = info.get("progress", None) or "N/A"

        if isinstance(progress, (int, float)):
            progress *= 100.0
            progress = "%.2f%%" % progress

        return [str(idx + 1), progress, operation, path]

    def display(self, window, ox=0, oy=0):
        x = self.x + ox
        y = self.y + oy

        window.addstr(y, x, "Workers:")
        y += 1
        height = 1

        workers = self.list = self.worker_owner.get_worker_list()

        rows = []
        colors = [None]

        self.viewport_size = (window.getmaxyx()[0] - y) // 2

        a = self.viewport_idx
        b = a + self.n_visible

        for i in range(a, b):
            rows.append(self.get_worker_columns(workers[i], i))

            if i == self.selection and self.focused:
                colors.append(self.highlight_pair)
            else:
                colors.append(None)

        height += common.display_table(y, x, window, self.columns, rows, colors)

        return height
