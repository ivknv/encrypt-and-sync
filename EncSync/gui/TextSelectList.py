#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk

class TextSelectList(gtk.TreeView):
    def __init__(self, column_name):
        self.liststore = gtk.ListStore(bool, str)
        gtk.TreeView.__init__(self, self.liststore)

        self.text_renderer = gtk.CellRendererText(xalign=0.0)
        self.toggle_renderer = gtk.CellRendererToggle(xalign=0.0)

        column1 = gtk.TreeViewColumn(column_name)
        column1.pack_start(self.toggle_renderer, False)
        column1.pack_start(self.text_renderer, True)

        column1.add_attribute(self.toggle_renderer, "active", 0)
        column1.add_attribute(self.text_renderer, "text", 1)

        self.append_column(column1)

        self.toggle_renderer.connect("toggled", self.toggled_handler)

    def toggled_handler(self, widget, path):
        self.liststore[path][0] = not self.liststore[path][0]
