#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import Element

class TargetManagerInfo(Element):
    def __init__(self, target_manager, root=None):
        Element.__init__(self, root)

        self.target_manager = target_manager
        self.manager_name = "<Target manager>"

    def display(self, window, ox=0, oy=0):
        x = self.x + ox
        y = self.y + oy

        if self.target_manager.is_alive():
            if self.target_manager.stopped:
                window.addstr(y, x, "%s is shutting down" % self.manager_name)
            else:
                window.addstr(y, x, "%s is running" % self.manager_name)
        else:
            window.addstr(y, x, "%s is not running" % self.manager_name)

        height = 2

        return height
