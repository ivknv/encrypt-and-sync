#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
from datetime import datetime

from gi.repository import Gtk as gtk
from gi.repository import GdkPixbuf as gdkPixbuf
from gi.repository import GObject as gobject
from gi.repository import GLib as glib

from .LoginForm import LoginForm
from .SyncScreen import EncSyncScreen
from .ScanScreen import EncScanScreen
from .DownloadsScreen import EncDownloadsScreen
from .ConfigEditor import EncConfigEditor

from ..YandexDiskApi import parse_date
from ..EncPath import EncPath

from . import GlobalState
from .. import paths

from .GlobalState import show_error

import threading

def get_time_offset():
    d = datetime.now()
    
    return d.timestamp() - datetime.utcfromtimestamp(d.timestamp()).timestamp()

def wrap_ret(f, v):
    def g(*args, **kwargs):
        f(*args, **kwargs)
        return v
    return g

def is_path_target(path_type, path):
    seps = {"local": os.path.sep, "remote": "/"}

    path = paths.dir_normalize(path)

    for t in GlobalState.encsync.targets:
        if path_type == "local":
            p = paths.from_sys(t[path_type])
        else:
            p = t[path_type]
        p = paths.dir_normalize(p)

        if paths.contains(p, path, seps[path_type]):
            return True
    return False

class FileList(gtk.Overlay):
    dirPixbuf = gdkPixbuf.Pixbuf.new_from_file("Icons/dir.png").scale_simple(32, 32, gdkPixbuf.InterpType.BILINEAR)
    filePixbuf = gdkPixbuf.Pixbuf.new_from_file("Icons/file.png").scale_simple(32, 32, gdkPixbuf.InterpType.BILINEAR)

    date_format = "%d.%m.%Y %H:%M:%S"

    def __init__(self):
        gtk.Overlay.__init__(self)
        self.scrolled_window = gtk.ScrolledWindow()

        self.liststore = gtk.ListStore(gdkPixbuf.Pixbuf, str, str, str, gobject.TYPE_PYOBJECT)
        self.treeview = gtk.TreeView(self.liststore)

        self.text_renderer = gtk.CellRendererText()
        self.pixbuf_renderer = gtk.CellRendererPixbuf()

        self.pixbuf_renderer.set_property('xalign', 0.0)

        column1 = gtk.TreeViewColumn("Name")
        column1.pack_start(self.pixbuf_renderer, False)
        column1.pack_start(self.text_renderer, True)

        column1.add_attribute(self.pixbuf_renderer, "pixbuf", 0)
        column1.add_attribute(self.text_renderer, "text", 2)

        column2 = gtk.TreeViewColumn("Modified")
        column2.pack_start(self.text_renderer, True)

        column2.add_attribute(self.text_renderer, "text", 3)

        self.treeview.append_column(column1)
        self.treeview.append_column(column2)

        self.treeview.connect("row-activated", self.row_activated_handler)
        self.treeview.connect("button-press-event", self.button_press_handler)

        self.menu = gtk.Menu()
        self.menuitem1 = gtk.MenuItem(label="Download")
        self.menu.append(self.menuitem1)

        self.menuitem1.connect("activate", self.download_handler)

        self.progress_bar = gtk.ProgressBar(valign=gtk.Align.END)

        self.path = EncPath(GlobalState.encsync)
        self.path.remote_prefix = ""
        self.path.path = ""

        self.update_thread = None

        for t in GlobalState.encsync.targets:
            self.add_row("d", t["remote"], "", b"")

        self.scrolled_window.add_with_viewport(self.treeview)
        self.add(self.scrolled_window)

    def refresh(self):
        if self.update_thread is None:
            if self.path.path == "" and self.path.remote_prefix == "":
                self.liststore.clear()
                for t in GlobalState.encsync.targets:
                    self.add_row("d", t["remote"], "", b"")
            else:
                self.update_thread = threading.Thread(target=self.update_rows, daemon=True)
                self.update_thread.start()

    def download_handler(self, widget):
        if GlobalState.synchronizer.is_alive():
            GlobalState.show_error("Synchronizer and downloader can't be run at the same time")
            return

        model, treeiter = self.treeview.get_selection().get_selected()

        if treeiter is None:
            source = self.path.path
            IVs = self.path.IVs
            action = gtk.FileChooserAction.CREATE_FOLDER
            target_type = "d"
        else:
            row = model[treeiter]
            if self.path.path == "" and self.path.remote_prefix == "":
                source = row[2]
                IVs = b""
            else:
                IVs = self.path.IVs + row[-1]
                source = paths.join(self.path.path, row[2])
            target_type = row[1]
            if target_type == "f":
                action = gtk.FileChooserAction.SAVE
            else:
                action = gtk.FileChooserAction.CREATE_FOLDER

        if source.endswith(".."):
            source = paths.split(self.path.path)[0]
            IVs = self.path.IVs[:-16]

        dialog = gtk.FileChooserDialog("Choose the destination folder",
                                       GlobalState.window, action,
                                       (gtk.STOCK_OPEN, gtk.ResponseType.OK,
                                        gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))

        dialog.set_current_name(paths.split(source)[1])

        response = dialog.run()

        filename = dialog.get_filename()
        dialog.destroy()

        if response != gtk.ResponseType.OK:
            return

        if is_path_target("remote", source):
            prefix = source
            source = "/"
        else:
            prefix = self.path.remote_prefix

        GlobalState.add_download(target_type, source, IVs, filename, prefix)
        GlobalState.downloader.start_if_not_alive()

    def show_progress_bar(self):
        self.progress_bar.set_fraction(0.0)
        self.add_overlay(self.progress_bar)
        self.show_all()

        return False

    def hide_progress_bar(self):
        self.remove(self.progress_bar)

        return False

    def get_filelist(self, path):
        flist = []
        time_offset = get_time_offset()

        for i in GlobalState.encsync.ynd.ls(path.remote_enc):
            data = i["data"] 
            data["name"], data["IVs"] = GlobalState.encsync.decrypt_path(data["name"])

            timestamp = time.mktime(parse_date(data["modified"])) + time_offset

            modified = datetime.fromtimestamp(timestamp)

            data["modified"] = modified.strftime(self.date_format)
            flist.append(data)
            yield (i["offset"], i["total"])

        flist.sort(key=lambda x: (x["type"], x["name"][:1].islower(), x["name"]))

        yield flist

    def enter_dir(self, path, IV=b""):
        if self.update_thread is None:
            if self.path.remote_prefix == "":
                assert(self.path.path == "")
                self.path.remote_prefix = path
                self.path.IVs = None
            else:
                self.path.IVs += IV
                self.path.path = paths.join(self.path.path, path)
            self.update_thread = threading.Thread(target=self.update_rows, daemon=True)
            self.update_thread.start()

    def update_rows(self):
        glib.idle_add(wrap_ret(self.show_progress_bar, False))

        flist = []

        try:
            for i in self.get_filelist(self.path):
                if type(i) == list:
                    flist = i
                else:
                    frac = float(i[0] + 1) / float(i[1])
                    glib.idle_add(wrap_ret(self.progress_bar.set_fraction, False), frac)
        except Exception as e:
            glib.idle_add(wrap_ret(show_error, False), "An error occured")

        def func():
            self.liststore.clear()

            if self.path != "":
                self.add_row("d", "..", "", b"")

            for i in flist:
                self.add_row(i["type"][0], i["name"], i["modified"], i["IVs"])

            self.hide_progress_bar()

            return False

        glib.idle_add(func)

        self.update_thread = None

    def exit_dir(self):
        if self.update_thread is None:
            new_path = paths.split(self.path.remote_enc)[0]
            if self.path.remote != "/" and is_path_target("remote", new_path):
                self.path.remote_prefix = new_path
                self.path.path = ""
                self.update_thread = threading.Thread(target=self.update_rows, daemon=True)
                self.update_thread.start()
            else:
                self.liststore.clear()
                self.path.path = ""
                self.path.remote_prefix = ""
                for t in GlobalState.encsync.targets:
                    self.add_row("d", t["remote"], "", b"")

    def add_row(self, filetype, name, modified, IVs):
        if filetype == "d":
            self.liststore.append([FileList.dirPixbuf, "d", name, modified, IVs])
        else:
            self.liststore.append([FileList.filePixbuf, "f", name, modified, IVs])

    def row_activated_handler(self, widget, treepath, column):
        model, treeiter = self.treeview.get_selection().get_selected()

        if treeiter is None:
            return

        sel = model[treeiter]
        
        if sel[2] == "..":
            self.exit_dir()
        elif sel[1] == "d":
            self.enter_dir(sel[2], sel[-1])

    def button_press_handler(self, widget, event):
        if event.button != 3: # Catch only right click
            return

        self.menu.popup(None, None, None, None, event.button, event.time)
        self.menu.show_all()

        return True

class EncViewer(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)

        self.loginform = LoginForm()
        self.loginform.connect("login-completed", self.login_handler)

        self.add(self.loginform)

    def login_handler(self, widget):
        self.remove(self.loginform)
        self.loginform = None

        notebook = gtk.Notebook()

        GlobalState.file_viewer = FileList()

        # Not using dict to preserve ordering
        pages = ("Sync", EncSyncScreen(),
                 "Scanner", EncScanScreen(),
                 "Downloads", EncDownloadsScreen(),
                 "Configure", EncConfigEditor(),
                 "Viewer", GlobalState.file_viewer)

        for label, page in zip(pages[::2], pages[1::2]):
            page.set_border_width(10)
            notebook.append_page(page, gtk.Label(label=label))

        self.add(notebook)

        self.show_all()
