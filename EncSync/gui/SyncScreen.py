#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk
from gi.repository import GLib as glib

from .TargetList import EncTargetList
from .TextSelectList import TextSelectList
from .WorkerMonitor import WorkerMonitor
from . import GlobalState
from ..Event import Receiver, ReceiverThread
from .DiffDisplayer import DiffDisplayer
import weakref
import threading

class SyncTargetList(gtk.TreeView):
    def __init__(self):
        self.liststore = gtk.ListStore(bool, bool, str, str)
        gtk.TreeView.__init__(self, self.liststore)

        for i in GlobalState.encsync.targets:
            self.liststore.append([True, True, i["local"], i["remote"]])

        self.text_renderer = gtk.CellRendererText(xalign=0.0)
        self.toggle_renderer = gtk.CellRendererToggle(xalign=0.0)

        renderers = {"text":   {"class": gtk.CellRendererText,
                                "instances": []},
                     "toggle": {"class": gtk.CellRendererToggle,
                                "instances": []}}

        attributes = {"text": "text",
                      "toggle": "active"}

        columns = ({"name": "Scan?",
                    "renderers": [{"type": "toggle",
                                   "index": 0,
                                   "properties": {},
                                   "expand": True}]},
                   {"name": "Local path",
                    "renderers": [{"type": "toggle",
                                   "index": 1,
                                   "properties": {"xalign": 0.0},
                                   "expand": False},
                                  {"type": "text",
                                   "index": 2,
                                   "properties": {},
                                   "expand": True}]},
                   {"name": "Remote path",
                    "renderers": [{"type": "text",
                                   "index": 3,
                                   "properties": {},
                                   "expand": True}]})

        for column_def in columns:
            column = gtk.TreeViewColumn(column_def["name"])
            for renderer_def in column_def["renderers"]:
                renderer_type = renderer_def["type"]
                expand        = renderer_def["expand"]
                attr          = attributes[renderer_type]
                idx           = renderer_def["index"]
                renderer      = renderers[renderer_type]["class"]()

                renderer_def["object"] = renderer

                for prop, value in renderer_def["properties"].items():
                    renderer.set_property(prop, value)

                column.pack_start(renderer, expand)
                column.add_attribute(renderer, attr, idx)

            self.append_column(column)

        for column_def in columns:
            for renderer_def in column_def["renderers"]:
                if renderer_def["type"] != "toggle":
                    continue

                renderer = renderer_def["object"]
                idx      = renderer_def["index"]
                renderer.connect("toggled", self.toggle_handler, idx)

    def toggle_handler(self, widget, path, idx):
        self.liststore[path][idx] = not self.liststore[path][idx]

class AddSyncTargetDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self, "Add sync targets", GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,
                             gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))
        
        box = self.get_content_area()

        self.target_list = SyncTargetList()

        box.pack_start(self.target_list, False, True, 0)

        self.show_all()

class IntegrityCheckDialog(gtk.Dialog):
    def __init__(self, target):
        gtk.Dialog.__init__(self, "Integrity check failed", GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,))
        
        box = self.get_content_area()
        box.set_border_width(10)
        box.set_spacing(10)

        label = gtk.Label(xalign=0)
        label.set_markup("<b><span font='18.0'>{}</span></b>".format(target.remote))

        message = "Integrity check failed\nHere's the list of differences after synchronization:"

        message_label = gtk.Label(label=message, xalign=0)

        diff_displayer = DiffDisplayer(target)

        box.pack_start(label, False, True, 0)
        box.pack_start(message_label, False, True, 0)
        box.pack_start(diff_displayer, False, True, 0)

        self.show_all()

class SyncTargetSetupDialog(gtk.Dialog):
    def __init__(self, target):
        gtk.Dialog.__init__(self, "Setup sync target", GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,
                             gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))
        
        box = self.get_content_area()
        box.set_border_width(10)
        box.set_spacing(10)

        label = gtk.Label(xalign=0)
        label.set_markup("<b><span font='18.0'>{}</span></b>".format(target.remote))

        diff_displayer = DiffDisplayer(target)

        self.skip_check_button = gtk.CheckButton(label="Skip integrity check",
                                                 xalign=0.0)
        self.skip_check_button.set_active(True)

        box.pack_start(label, False, True, 0)
        box.pack_start(diff_displayer, False, True, 0)
        box.pack_start(self.skip_check_button, False, True, 0)

        self.show_all()

    def get_skip_check(self):
        return self.skip_check_button.get_active()

class EncSyncScreen(gtk.ScrolledWindow):
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)

        self.vbox = gtk.VBox(spacing=5)
        self.add_button = gtk.Button(label="Add sync target", xalign=0.0)
        self.sync_progress = EncSyncProgress()
        self.worker_monitor = WorkerMonitor(GlobalState.synchronizer)

        self.hbox = gtk.HBox()

        self.hbox.pack_start(self.add_button, False, True, 0)
        self.vbox.pack_start(self.hbox, False, True, 0)
        self.vbox.pack_start(self.sync_progress, True, True, 0)
        self.vbox.pack_start(self.worker_monitor, True, True, 0)

        self.add(self.vbox)

        self.add_button.connect("clicked", self.add_button_handler)

        self.scan_receiver = Receiver()
        self.dialog_receiver = ReceiverThread()

        self.dialog_lock = threading.Lock()

        self.scan_receiver.add_callback("scan_finished", self.scan_finished_callback)

        self.dialog_receiver.add_callback("scan_finished", self.show_post_scan_dialog)
        self.dialog_receiver.add_callback("integrity_check_failed", self.integrity_check_failed_callback)

        self.dialog_receiver.start()

        self.connect("delete-event", self.on_delete)

    def on_delete(self):
        self.dialog_receiver.stop()

    def scan_finished_callback(self, event):
        target = event.emitter
        target.change_status("suspended")

    def show_post_scan_dialog(self, event):
        target = event.emitter

        def func():
            with self.dialog_lock:
                dialog = SyncTargetSetupDialog(target)
                response = dialog.run()

                if response == gtk.ResponseType.OK:
                    target.stage = "rm"
                    target.skip_integrity_check = dialog.get_skip_check()
                    target.change_status("pending")

                    if target not in GlobalState.synchronizer.get_targets():
                        GlobalState.synchronizer.add_existing_target(target)
                    GlobalState.synchronizer.start_if_not_alive()

                dialog.destroy()

            return False

        with self.dialog_lock:
            glib.idle_add(func)

    def integrity_check_failed_callback(self, event):
        target = event.emitter

        def func():
            with self.dialog_lock:
                dialog = IntegrityCheckDialog(target)
                response = dialog.run()
                dialog.destroy()

            return False

        with self.dialog_lock:
            glib.idle_add(func)

    def add_button_handler(self, widget):
        add_dialog = AddSyncTargetDialog()

        while True:
            response = add_dialog.run()

            if response != gtk.ResponseType.OK:
                add_dialog.destroy()
                return

            msg_template = "Synchronizer and {} can't be run at the same time"

            if GlobalState.scanner.is_alive():
                GlobalState.show_error(msg_template.format("scanner"))
            elif GlobalState.downloader.is_alive():
                GlobalState.show_error(msg_template.format("downloader"))
            else:
                break

        liststore = add_dialog.target_list.liststore

        for row in liststore:
            enable_scan = row[0]
            active = row[1]

            if not active:
                continue

            local = row[2]
            remote = row[3]

            target = GlobalState.add_sync_target(enable_scan, remote, local)

            target.add_receiver(self.scan_receiver)
            target.add_receiver(self.dialog_receiver)

        GlobalState.synchronizer.start_if_not_alive()

        add_dialog.destroy()

class EncSyncProgress(gtk.ScrolledWindow):
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)

        self.treeview = gtk.TreeView(GlobalState.sync_targets)

        self.cell1 = gtk.CellRendererProgress()
        self.cell2 = gtk.CellRendererText()
        self.cell3 = gtk.CellRendererText()
        self.cell4 = gtk.CellRendererText()
        self.cell5 = gtk.CellRendererText()

        self.menu = gtk.Menu()
        self.menuitem1 = gtk.MenuItem(label="Stop")
        self.menuitem2 = gtk.MenuItem(label="Resume")
        self.menu.append(self.menuitem1)
        self.menu.append(self.menuitem2)

        self.menuitem1.connect("activate", self.stop_handler)
        self.menuitem2.connect("activate", self.resume_handler)

        self.column1 = gtk.TreeViewColumn("%", self.cell1, value=0)

        self.column2 = gtk.TreeViewColumn("Status", self.cell2, text=1)

        self.column3 = gtk.TreeViewColumn("Stage", self.cell3, text=2)

        self.column4 = gtk.TreeViewColumn("Source", self.cell3, text=4)
        self.column5 = gtk.TreeViewColumn("Destination", self.cell4, text=3)

        self.treeview.append_column(self.column1)
        self.treeview.append_column(self.column2)
        self.treeview.append_column(self.column3)
        self.treeview.append_column(self.column4)
        self.treeview.append_column(self.column5)

        self.add_with_viewport(self.treeview)

        self.background_worker = None

        self.treeview.connect("button-press-event", self.button_press_handler)

        glib.timeout_add(1000, self.update_rows, weakref.finalize(self, lambda: None))

    def stop_handler(self, widget):
        model, treeiter = self.treeview.get_selection().get_selected()

        if treeiter is None:
            if self.background_worker is None:
                self.background_worker = threading.Thread(target=GlobalState.synchronizer.stop)
                self.background_worker.start()
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
            if target not in GlobalState.synchronizer.get_targets():
                GlobalState.synchronizer.add_existing_target(target)
            GlobalState.synchronizer.start_if_not_alive()

    @staticmethod # that's not a typo
    def update_rows(weak_self):
        if not weak_self.alive:
            return False

        dispatcher = GlobalState.synchronizer.dispatcher

        for row in GlobalState.sync_targets:
            task = row[-1]
            try:
                row[0] = int(task.progress["finished"] / task.total_children * 100)
            except ZeroDivisionError:
                row[0] = 100 if task.status == "finished" else 0

            row[1] = task.status.capitalize()

            if dispatcher.stage is None:
                row[2] = "None"
            elif task == dispatcher.cur_target:
                row[2] = dispatcher.stage["name"].capitalize()

        return True

    def button_press_handler(self, widget, event):
        if event.button != 3: # Catch only right click
            return

        self.menu.popup(None, None, None, None, event.button, event.time)
        self.menu.show_all()

        return True
