#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk
from gi.repository import GLib as glib
from gi.repository import GObject as gobject

import threading
import weakref

from . import GlobalState
from .WorkerMonitor import WorkerMonitor

class EncDownloads(gtk.ScrolledWindow):
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)

        self.treeview = gtk.TreeView(GlobalState.downloads)

        self.cell1 = gtk.CellRendererProgress()
        self.cell2 = gtk.CellRendererText()
        self.cell3 = gtk.CellRendererText()
        self.cell4 = gtk.CellRendererText()

        self.column1 = gtk.TreeViewColumn("%", self.cell1, value=0)

        self.column2 = gtk.TreeViewColumn("Status", self.cell2, text=1)

        self.column3 = gtk.TreeViewColumn("Source", self.cell2, text=2)

        self.column4 = gtk.TreeViewColumn("Destination", self.cell3, text=3)

        self.menu = gtk.Menu()
        self.menuitem1 = gtk.MenuItem(label="Stop")
        self.menuitem2 = gtk.MenuItem(label="Resume")
        self.menu.append(self.menuitem1)
        self.menu.append(self.menuitem2)

        self.menuitem1.connect("activate", self.stop_handler)
        self.menuitem2.connect("activate", self.resume_handler)

        self.treeview.connect("button-press-event", self.button_press_handler)

        self.treeview.append_column(self.column1)
        self.treeview.append_column(self.column2)
        self.treeview.append_column(self.column3)
        self.treeview.append_column(self.column4)

        self.add_with_viewport(self.treeview)

        glib.timeout_add(1000, self.update_rows, weakref.finalize(self, lambda: None))

    def stop_handler(self, widget):
        model, treeiter = self.treeview.get_selection().get_selected()

        if treeiter is None:
            GlobalState.downloader.stop()
            return

        row = model[treeiter]
        target = row[-1]

        if target.status is None or target.status == "pending":
            target.change_status("suspended")

    def resume_handler(self, widget):
        model, treeiter = self.treeview.get_selection().get_selected()

        if treeiter is None:
            return

        row = model[treeiter]
        target = row[-1]

        if target.status == "suspended":
            target.change_status("pending")
            if target not in GlobalState.downloader.get_targets():
                GlobalState.downloader.add_target(target)
            GlobalState.downloader.start_if_not_alive()

    def button_press_handler(self, widget, event):
        if event.button != 3: # Catch only right click
            return

        self.menu.popup(None, None, None, None, event.button, event.time)
        self.menu.show_all()

        return True

    @staticmethod # that's not a typo
    def update_rows(weak_self):
        if not weak_self.alive:
            return False

        for row in GlobalState.downloads:
            target = row[-1]
            try:
                if target.type == "file":
                    row[0] = int(float(target.downloaded) / float(target.size) * 100)

                    if target.status == "finished":
                        row[0] = 100
                else:
                    row[0] = int(target.progress["finished"] / target.total_children * 100)
            except ZeroDivisionError:
                row[0] = 0

            row[1] = str(target.status).capitalize()

        return True

class EncDownloadsScreen(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self, spacing=5)

        self.label = gtk.Label(label="Downloads:", xalign=0.0)

        self.downloads = EncDownloads()
        self.worker_monitor = WorkerMonitor(GlobalState.downloader)

        self.pack_start(self.label, False, True, 0)
        self.pack_start(self.downloads, True, True, 0)
        self.pack_start(self.worker_monitor, True, True, 0)
