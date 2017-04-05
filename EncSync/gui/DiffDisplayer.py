#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk
from .. import SyncList
from . import GlobalState

class DiffListDialog(gtk.Dialog):
    def __init__(self, title, diffs):
        gtk.Dialog.__init__(self, title, GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,))

        self.set_default_size(640, 480)

        box = self.get_content_area()
        box.set_border_width(10)

        scrolled_window = gtk.ScrolledWindow()

        text_renderer = gtk.CellRendererText()

        liststore = gtk.ListStore(str, str)

        for diff in diffs:
            path = diff[2].remote

            liststore.append([{"f": "File",
                               "d": "Folder"}[diff[1]],
                              path])

        treeview = gtk.TreeView(liststore)

        column1 = gtk.TreeViewColumn("Type", text_renderer, text=0)
        column2 = gtk.TreeViewColumn("Path", text_renderer, text=1)

        treeview.append_column(column1)
        treeview.append_column(column2)

        scrolled_window.add(treeview)

        box.pack_start(scrolled_window, True, True, 0)

        self.show_all()

class DiffDisplayer(gtk.Grid):
    def __init__(self, target):
        gtk.Grid.__init__(self, column_spacing=15, row_spacing=7)

        difflist = GlobalState.difflist

        self.target = target

        upload_count = difflist.count_files_differences(target.local, target.remote)
        new_dirs_count = difflist.count_dirs_differences(target.local, target.remote)
        removal_count = difflist.count_rm_differences(target.local, target.remote)

        upload_count_label = gtk.Label(label="Files to upload: {}".format(upload_count),
                                       xalign=0.0)
        new_dirs_count_label = gtk.Label(label="New directories: {}".format(new_dirs_count),
                                         xalign=0.0)
        removal_count_label = gtk.Label(label="Removal: {}".format(removal_count),
                                        xalign=0.0)

        show_upload_button = gtk.Button(label="Show")
        show_new_dirs_button = gtk.Button(label="Show")
        show_removal_button = gtk.Button(label="Show")

        self.add(upload_count_label)
        self.attach_next_to(show_upload_button, upload_count_label,
                            gtk.PositionType.RIGHT, 1, 1)
        self.attach_next_to(new_dirs_count_label, upload_count_label,
                            gtk.PositionType.BOTTOM, 1, 1)
        self.attach_next_to(show_new_dirs_button, new_dirs_count_label,
                            gtk.PositionType.RIGHT, 1, 1)
        self.attach_next_to(removal_count_label, new_dirs_count_label,
                            gtk.PositionType.BOTTOM, 1, 1)
        self.attach_next_to(show_removal_button, removal_count_label,
                            gtk.PositionType.RIGHT, 1, 1)

        show_upload_button.connect("clicked", self.show_upload)
        show_new_dirs_button.connect("clicked", self.show_new_dirs)
        show_removal_button.connect("clicked", self.show_removal)

    def show_diffs(self, diff_type, widget):
        difflist = GlobalState.difflist

        assert(diff_type in {"rm", "dirs", "files"})

        titles = {"rm": "Removal",
                  "dirs": "New directories",
                  "files": "Upload"}

        funcs = {"rm": difflist.select_rm_differences,
                 "dirs": difflist.select_dirs_differences,
                 "files": difflist.select_files_differences}

        diffs = funcs[diff_type](self.target.local, self.target.remote)

        title = titles[diff_type]

        dialog = DiffListDialog(title, diffs)

        response = dialog.run()

        dialog.destroy()

    def show_upload(self, widget):
        self.show_diffs("files", widget)

    def show_new_dirs(self, widget):
        self.show_diffs("dirs", widget)

    def show_removal(self, widget):
        self.show_diffs("rm", widget)
