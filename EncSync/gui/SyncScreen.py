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
        self.liststore = gtk.ListStore(bool, str, str)
        gtk.TreeView.__init__(self, self.liststore)

        for i in GlobalState.encsync.targets:
            self.liststore.append([True, i["local"], i["remote"]])

        self.text_renderer = gtk.CellRendererText(xalign=0.0)
        self.toggle_renderer = gtk.CellRendererToggle(xalign=0.0)

        column1 = gtk.TreeViewColumn("Local path")
        column1.pack_start(self.toggle_renderer, False)
        column1.pack_start(self.text_renderer, True)

        column1.add_attribute(self.toggle_renderer, "active", 0)
        column1.add_attribute(self.text_renderer, "text", 1)

        column2 = gtk.TreeViewColumn("Remote path", self.text_renderer, text=2)

        self.append_column(column1)
        self.append_column(column2)

        self.toggle_renderer.connect("toggled", self.toggle_handler)

    def toggle_handler(self, widget, path):
        self.liststore[path][0] = not self.liststore[path][0]

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

            if GlobalState.scanner.is_alive():
                msg = "Synchronizer and scanner cannot run at the same time"
                dialog = gtk.MessageDialog(GlobalState.window, 0, gtk.MessageType.INFO,
                                           gtk.ButtonsType.OK, msg)
                dialog.run()
                dialog.destroy()
            else:
                break

        liststore = add_dialog.target_list.liststore

        for row in liststore:
            active = row[0]

            if not active:
                continue

            local = row[1]
            remote = row[2]

            target = GlobalState.add_sync_target(remote, local)

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
