#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk
from gi.repository import GLib as glib
from gi.repository import GObject as gobject

from . import GlobalState
import weakref

class WorkerMonitor(gtk.ScrolledWindow):
    def __init__(self, obj):
        gtk.ScrolledWindow.__init__(self)

        self.liststore = gtk.ListStore(str, int, str, str, str, gobject.TYPE_PYOBJECT)
        self.treeview = gtk.TreeView(self.liststore)

        self.obj = obj

        cell_renderers = {"text":     gtk.CellRendererText(),
                          "progress": gtk.CellRendererProgress()}
        column_attributes = {"text":     "text",
                             "progress": "value"}

        columns = (("No.", "text"),
                   ("%", "progress"),
                   ("Operation", "text"),
                   ("Path", "text"))

        for i, col in zip(range(len(columns)), columns):
            column_name, column_type = col

            cell = cell_renderers[column_type]
            attr = column_attributes[column_type]

            column = gtk.TreeViewColumn(column_name, cell, **{attr: i})
            self.treeview.append_column(column)

        glib.timeout_add(300, self.update_rows, weakref.finalize(self, lambda: None))

        self.add_with_viewport(self.treeview)

    @staticmethod
    def update_rows(weak_self):
        if not weak_self.alive:
            return False

        glib.idle_add(WorkerMonitor._update_rows, weak_self)

        return True

    @staticmethod
    def _update_rows(weak_self):
        obj = weak_self.peek()[0].obj

        liststore = weak_self.peek()[0].liststore

        if not obj.is_alive():
            liststore.clear()
            return

        dead_worker_idxs = set()

        cur_workers = tuple(i[-1] for i in liststore)

        for row in liststore:
            worker = row[-1]
            if not worker.is_alive():
                liststore.remove(row.iter)

        for i in dead_worker_idxs:
            liststore.remove(liststore.get_iter(i))

        workers = obj.get_worker_list()

        cur_worker_ids = set(w.ident for w in cur_workers)

        for worker in workers:
            if worker.is_alive() and worker.ident not in cur_worker_ids:
                cur_worker_ids.add(worker.ident)
                liststore.append(["", 0, "", "", "", worker])

        for i, row in zip(range(len(liststore)), liststore):
            row[0] = str(i + 1)

            worker = row[-1]
            info = worker.get_info()

            row[1] = int(info.get("progress", 0) * 100)
            row[2] = info.get("operation", "N/A").capitalize()
            row[3] = info.get("path", "N/A")
