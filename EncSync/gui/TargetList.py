#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk
from . import GlobalState
from collections import Counter

class EncTargetList(gtk.TreeView):
    def __init__(self):
        self.liststore = gtk.ListStore(str, str)
        gtk.TreeView.__init__(self, self.liststore)

        for i in GlobalState.encsync.targets:
            self.liststore.append([i["local"], i["remote"]])

        self.text_renderer = gtk.CellRendererText(xalign=0.0)

        column1 = gtk.TreeViewColumn("Local path")
        column1.pack_start(self.text_renderer, True)

        column1.add_attribute(self.text_renderer, "text", 0)

        column2 = gtk.TreeViewColumn("Remote path", self.text_renderer, text=1)

        self.append_column(column1)
        self.append_column(column2)

    def update(self):
        self.liststore.clear()

        for i in GlobalState.encsync.targets:
            self.liststore.append([i["local"], i["remote"]])
