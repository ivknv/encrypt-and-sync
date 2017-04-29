#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk
from gi.repository import GLib as glib

from .TextSelectList import TextSelectList
from .WorkerMonitor import WorkerMonitor
from .gtk_setup import gtk_setup
from . import GlobalState
from ..Event import ReceiverThread
from ..SyncList import DuplicateList

import weakref
import threading

class ScanDialog(gtk.Dialog):
    def __init__(self, scan_type):
        assert(scan_type == "local" or scan_type == "remote")

        if scan_type == "local":
            title = "Scan local directories"
        else:
            title = "Scan yandex disk directories"


        gtk.Dialog.__init__(self, title, GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,
                             gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))
 
        box = self.get_content_area()

        self.dir_list = TextSelectList("Directory")
        for i in GlobalState.encsync.targets:
            if scan_type == "local":
                self.dir_list.liststore.append([False, i["local"]])
            else:
                self.dir_list.liststore.append([False, i["remote"]])

        box.pack_start(self.dir_list, False, True, 0)

        self.show_all()

    def get_enabled(self):
        return (i[1] for i in self.dir_list.liststore if i[0])

class DuplicateListDialog(gtk.Dialog):
    def __init__(self, target):
        gtk.Dialog.__init__(self, "Duplicates", GlobalState.window)

        self.liststore = gtk.ListStore(str, str)
        self.treeview = gtk.TreeView()

        duplist = DuplicateList()

        for i in duplist.find_children(target.path):
            path = GlobalState.encsync.decrypt_path(i[1], target.path)[0]
            self.liststore.append([{"f": "File", "d": "Dir"}[i[0]], path])

        definition = {"type": "dialog",
                      "object": self,
                      "properties": {},
                      "buttons": (gtk.STOCK_OK, gtk.ResponseType.OK),
                      "children": [{"type": "treeview",
                                    "object": self.treeview,
                                    "model": self.liststore,
                                    "expand": True,
                                    "fill": False,
                                    "columns": [{"properties": {"title": "Type"},
                                                 "renderers": [{"type": "text",
                                                                "index": 0,
                                                                "expand": False}]},
                                                {"properties": {"title": "Path"},
                                                 "renderers": [{"type": "text",
                                                                "index": 1,
                                                                "expand": True}]}]}]}
        gtk_setup(definition)

        self.show_all()

class EncScanScreen(gtk.ScrolledWindow):
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)

        self.vbox = gtk.VBox(spacing=5)
        self.scan_remote_button = gtk.Button(label="Scan remote disk")
        self.scan_local_button = gtk.Button(label="Scan local disk")

        self.hbox = gtk.HBox(spacing=10)

        self.scan_progress = EncScanProgress()

        self.monitor = WorkerMonitor(GlobalState.scanner)

        self.hbox.pack_start(self.scan_remote_button, False, True, 0)
        self.hbox.pack_start(self.scan_local_button, False, True, 0)
        self.vbox.pack_start(self.hbox, False, True, 0)
        self.vbox.pack_start(self.scan_progress, True, True, 0)
        self.vbox.pack_start(self.monitor, True, True, 0)

        self.add(self.vbox)

        self.scan_local_button.connect("clicked", self.scan_local_button_handler)
        self.scan_remote_button.connect("clicked", self.scan_remote_button_handler)

        self.dialog_lock = threading.Lock()
        self.dialog_receiver = ReceiverThread()

        self.dialog_receiver.add_callback("scan_finished", self.show_duplicates)

        self.dialog_receiver.start()

        self.connect("delete-event", self.on_delete)

    def on_delete(self):
        self.dialog_receiver.stop()

    def show_duplicates(self, event):
        target = event.emitter

        if target.type != "remote":
            return

        duplist = DuplicateList()

        if duplist.is_empty(target.path):
            return

        def func():
            with self.dialog_lock:
                dialog = DuplicateListDialog(target)
                response = dialog.run()

                dialog.destroy()

            return False

        with self.dialog_lock:
            glib.idle_add(func)

    def scan_button_handler(self, scan_type, widget):
        dialog = ScanDialog(scan_type)

        while True:
            response = dialog.run()

            if response != gtk.ResponseType.OK:
                dialog.destroy()
                return

            if GlobalState.synchronizer.is_alive():
                msg = "Synchronizer and scanner cannot run at the same time"
                msg_dialog = gtk.MessageDialog(GlobalState.window, 0, gtk.MessageType.INFO,
                                               gtk.ButtonsType.OK, msg)
                msg_dialog.run()
                msg_dialog.destroy()
            else:
                break

        for i in dialog.get_enabled():
            target = GlobalState.add_scan_target(scan_type, i)
            target.add_receiver(self.dialog_receiver)

        GlobalState.scanner.start_if_not_alive()

        dialog.destroy()

    def scan_local_button_handler(self, widget):
        self.scan_button_handler("local", widget)

    def scan_remote_button_handler(self, widget):
        self.scan_button_handler("remote", widget)

class EncScanProgress(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self, spacing=10)

        self.treeview = gtk.TreeView(GlobalState.scan_targets)

        self.cell1 = gtk.CellRendererText()

        self.menu = gtk.Menu()
        self.menuitem1 = gtk.MenuItem(label="Stop")
        self.menuitem2 = gtk.MenuItem(label="Resume")
        self.menu.append(self.menuitem1)
        self.menu.append(self.menuitem2)

        self.menuitem1.connect("activate", self.stop_handler)
        self.menuitem2.connect("activate", self.resume_handler)

        self.column1 = gtk.TreeViewColumn("Status", self.cell1, text=0)

        self.column2 = gtk.TreeViewColumn("Type", self.cell1, text=1)

        self.column3 = gtk.TreeViewColumn("Path", self.cell1, text=2)

        self.treeview.append_column(self.column1)
        self.treeview.append_column(self.column2)
        self.treeview.append_column(self.column3)

        self.pack_start(self.treeview, False, True, 0)

        self.background_worker = None

        self.treeview.connect("button-press-event", self.button_press_handler)

        glib.timeout_add(1000, self.update_rows, weakref.finalize(self, lambda: None))

    def stop_handler(self, widget):
        model, treeiter = self.treeview.get_selection().get_selected()

        if treeiter is None:
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
            if target not in GlobalState.scanner.targets:
                GlobalState.scanner.add_target(target)
            GlobalState.scanner.start_if_not_alive()

    @staticmethod # that's not a typo
    def update_rows(weak_self):
        if not weak_self.alive:
            return False

        for row in GlobalState.scan_targets:
            target = row[3]
            row[0] = str(target.status).capitalize()
            row[1] = target.type.capitalize()
            row[2] = target.path

        return True

    def button_press_handler(self, widget, event):
        if event.button != 3: # Catch only right click
            return

        self.menu.popup(None, None, None, None, event.button, event.time)
        self.menu.show_all()

        return True
