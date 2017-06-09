#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from . import Element

class RootElement(Element):
    def __init__(self):
        Element.__init__(self, self)

        self.focused_element = None
        self.elements = []

        self.stop_getch = False

    def getch_stop_condition(self):
        return self.stop_getch

    def handle_key(self, k):
        if self.focused_element is not None:
            self.focused_element.handle_key(k)

        Element.handle_key(self, k)

    def getch_loop(self, window):
        while not self.getch_stop_condition():
            k = window.getch()

            self.handle_key(k)

    def start_getch(self, window, daemon=True):
        thread = threading.Thread(target=self.getch_loop, args=(window,), daemon=daemon)
        thread.start()
        return thread

    def add_element(self, element):
        self.elements.append(element)
        element.root = self

    def display(self, window, ox=0, oy=0):
        x = self.x + ox
        y = self.y + oy

        height = 0

        for element in self.elements:
            h = element.display(window, x, y + height)
            height += h

        return height

    def update_screen(self, window, ox=0, oy=0):
        window.clear()

        self.display(window, ox, oy)

        window.refresh()
