#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import Element

class ScrollableList(Element):
    def __init__(self, values=None, root=None):
        Element.__init__(self, root)

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
        try:
            self._selection = value % self.length
        except ZeroDivisionError:
            self._selection = 0

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
        try:
            self._viewport_idx = value % self.length
        except ZeroDivisionError:
            self._viewport_idx = 0

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

    @property
    def visible_list(self):
        return self.list[self.viewport_idx:self.viewport_idx + self.n_visible]
