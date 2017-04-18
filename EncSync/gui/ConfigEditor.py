#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk

from .TargetList import EncTargetList
from . import GlobalState

class EncEditKeyDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self, "Edit key", GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,
                             gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))
        
        box = self.get_content_area()

        self.entry = gtk.Entry(placeholder_text="New key", visibility=False)
        self.entry.set_text(GlobalState.encsync.plain_key)
        self.show_key_checkbox = gtk.CheckButton(label="Show key")
        self.show_key_checkbox.set_active(False)

        self.show_key_checkbox.connect("toggled", self.show_key_handler)

        box.pack_start(self.entry, False, True, 0)
        box.pack_start(self.show_key_checkbox, False, True, 0)

        self.show_all()

    def show_key_handler(self, widget):
        if widget.get_active():
            self.entry.set_visibility(True)
        else:
            self.entry.set_visibility(False)

class EncEditMasterKeyDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self, "Edit master password", GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,
                             gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))
        
        box = self.get_content_area()

        self.entry = gtk.Entry(placeholder_text="New master password",
                               visibility=False)
        self.confirm_entry = gtk.Entry(placeholder_text="Confirm master password",
                                       visibility=False)
        
        box.pack_start(self.entry, False, True, 0)
        box.pack_start(self.confirm_entry, False, True, 0)

        self.show_all()

class EncEditNumThreadsDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self, "Edit thread numbers", GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,
                             gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))
        
        box = self.get_content_area()

        self.label1 = gtk.Label(label="Downloader threads:", xalign=0.0)
        self.downloader_entry = gtk.Entry(placeholder_text="Downloader threads")
        self.downloader_entry.set_text(str(GlobalState.encsync.download_threads))

        self.label2 = gtk.Label(label="Synchronizer threads:", xalign=0.0)
        self.synchronizer_entry = gtk.Entry(placeholder_text="Synchronizer threads")
        self.synchronizer_entry.set_text(str(GlobalState.encsync.sync_threads))

        self.label3 = gtk.Label(label="Scanner threads:", xalign=0.0)
        self.scanner_entry = gtk.Entry(placeholder_text="Scanner threads")
        self.scanner_entry.set_text(str(GlobalState.encsync.scan_threads))

        box.pack_start(self.label1, False, True, 0)
        box.pack_start(self.downloader_entry, False, True, 0)
        box.pack_start(self.label2, False, True, 0)
        box.pack_start(self.synchronizer_entry, False, True, 0)
        box.pack_start(self.label3, False, True, 0)
        box.pack_start(self.scanner_entry, False, True, 0)

        self.show_all()

    def get_n_downloader_threads(self):
        return int(self.downloader_entry.get_text())

    def get_n_synchronizer_threads(self):
        return int(self.synchronizer_entry.get_text())

    def get_n_scanner_threads(self):
        return int(self.scanner_entry.get_text())

    def validate(self):
        try:
            return all([self.get_n_downloader_threads() > 0,
                        self.get_n_synchronizer_threads() > 0,
                        self.get_n_scanner_threads() > 0])
        except ValueError:
            return False

class EncEditTargetDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self, "Add target", GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,
                             gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))
        
        box = self.get_content_area()
        box.set_spacing(5)

        self.local_entry = gtk.Entry(placeholder_text="Local path")
        self.local_choose = gtk.Button(label="Choose")
        self.remote_entry = gtk.Entry(placeholder_text="Remote path")

        self.hbox1 = gtk.HBox(spacing=5)
        self.hbox2 = gtk.HBox(spacing=5)

        self.hbox1.pack_start(self.local_entry, False, True, 0)
        self.hbox1.pack_start(self.local_choose, False, True, 0)
        self.hbox2.pack_start(self.remote_entry, False, True, 0)

        box.pack_start(self.hbox1, False, True, 0)
        box.pack_start(self.hbox2, False, True, 0)

        self.local_choose.connect("clicked", self.local_choose_handler)

        self.show_all()

    def local_choose_handler(self, widget):
        dialog = gtk.FileChooserDialog("Choose the local folder",
                                       GlobalState.window, gtk.FileChooserAction.CREATE_FOLDER,
                                       (gtk.STOCK_OPEN, gtk.ResponseType.OK,
                                        gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))
        
        response = dialog.run()

        if response != gtk.ResponseType.OK:
            dialog.destroy()
            return

        self.local_entry.set_text(dialog.get_filename())

        dialog.destroy()

class EncEditSpeedLimitDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self, "Edit speed limits", GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,
                             gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))
        
        box = self.get_content_area()
        box.set_spacing(3)

        self.label1 = gtk.Label(label="Download speed limit [KB/s]:", xalign=0.0)
        self.label2 = gtk.Label(label="Upload speed limit [KB/s]:", xalign=0.0)

        self.download_limit_entry = gtk.Entry(placeholder_text="Download speed limit")
        self.upload_limit_entry = gtk.Entry(placeholder_text="Upload speed limit")
        self.download_limit_entry.set_text(str(GlobalState.encsync.download_limit // 1024))
        self.upload_limit_entry.set_text(str(GlobalState.encsync.upload_limit // 1024))

        box.pack_start(self.label1, False, True, 0)
        box.pack_start(self.download_limit_entry, False, True, 0)
        box.pack_start(self.label2, False, True, 0)
        box.pack_start(self.upload_limit_entry, False, True, 0)

        self.show_all()

    def get_upload_limit(self):
        text = self.upload_limit_entry.get_text()

        return int(text) * 1024

    def get_download_limit(self):
        text = self.download_limit_entry.get_text()

        return int(text) * 1024

    def validate(self):
        try:
            self.get_upload_limit()
            self.get_download_limit()

            return True
        except ValueError:
            return False

class EncConfigEditor(gtk.ScrolledWindow):
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)

        self.vbox = gtk.VBox(spacing=5)

        self.edit_limits_button = gtk.Button(label="Edit speed limits", xalign=0)

        self.edit_n_threads_button = gtk.Button(label="Edit number of threads", xalign=0)

        self.edit_key_button = gtk.Button(label="Edit key", xalign=0)
        self.edit_master_key_button = gtk.Button(label="Edit master password", xalign=0)

        self.edit_key_button.connect("clicked", self.edit_key_handler)
        self.edit_master_key_button.connect("clicked", self.edit_master_key_handler)

        self.target_label = gtk.Label(label="Sync targets:", xalign=0.0)
        self.target_list = EncTargetList()
        self.add_target_button = gtk.Button(label="Add target", xalign=0.0)

        self.save_button = gtk.Button(label="Save", xalign=0.0)

        self.hbox0 = gtk.HBox()
        self.hbox0.pack_start(self.edit_limits_button, False, True, 0)

        self.hbox1 = gtk.HBox()
        self.hbox1.pack_start(self.edit_n_threads_button, False, True, 0)

        self.hbox2 = gtk.HBox(spacing=10)
        self.hbox2.pack_start(self.edit_key_button, False, True, 0)
        self.hbox2.pack_start(self.edit_master_key_button, False, True, 0)

        self.hbox3 = gtk.HBox()
        self.hbox3.pack_start(self.add_target_button, False, True, 0)

        self.hbox4 = gtk.HBox()
        self.hbox4.pack_start(self.save_button, False, True, 0)

        self.vbox.pack_start(self.hbox0, False, True, 0)
        self.vbox.pack_start(self.hbox1, False, True, 0)
        self.vbox.pack_start(self.hbox2, False, True, 0)
        self.vbox.pack_start(self.target_label, False, True, 0)
        self.vbox.pack_start(self.target_list, False, True, 0)
        self.vbox.pack_start(self.hbox3, False, True, 0)
        self.vbox.pack_start(self.hbox4, False, True, 0)

        self.add_with_viewport(self.vbox)

        self.menu = gtk.Menu()
        self.menuitem1 = gtk.MenuItem(label="Edit")
        self.menuitem2 = gtk.MenuItem(label="Remove")
        self.menu.append(self.menuitem1)
        self.menu.append(self.menuitem2)

        self.edit_limits_button.connect("clicked", self.edit_limits_handler)
        self.edit_n_threads_button.connect("clicked", self.edit_n_threads_handler)

        self.add_target_button.connect("clicked", self.add_target_handler)

        self.target_list.connect("button-press-event", self.list_button_press_handler)

        self.menuitem1.connect("activate", self.target_edit_handler)
        self.menuitem2.connect("activate", self.target_remove_handler)

        self.save_button.connect("clicked", self.save_handler)

    def save_handler(self, widget):
        GlobalState.encsync.store_config("config.json")

    def target_edit_handler(self, widget):
        model, treeiter = self.target_list.get_selection().get_selected()

        if treeiter is None:
            return

        row = model[treeiter]

        local, remote = row

        dialog = EncEditTargetDialog()
        dialog.local_entry.set_text(local)
        dialog.remote_entry.set_text(remote)
        response = dialog.run()

        if response != gtk.ResponseType.OK:
            dialog.destroy()
            return

        for i in GlobalState.encsync.targets:
            if i["local"] == local and i["remote"] == remote:
                target = i

        local = dialog.local_entry.get_text()
        remote = dialog.remote_entry.get_text()

        target["local"] = local
        target["remote"] = remote
        self.target_list.update()

        GlobalState.file_viewer.refresh()

        dialog.destroy()

    def target_remove_handler(self, widget):
        model, treeiter = self.target_list.get_selection().get_selected()

        if treeiter is None:
            return

        row = model[treeiter]

        local, remote = row

        i = GlobalState.encsync.targets.index({"local": local, "remote": remote})

        if i != -1:
            GlobalState.encsync.targets.pop(i)

        self.target_list.update()
        GlobalState.file_viewer.refresh()

    def list_button_press_handler(self, widget, event):
        if event.button != 3: # Catch only right click
            return

        self.menu.popup(None, None, None, None, event.button, event.time)
        self.menu.show_all()

        return True

    def add_target_handler(self, widget):
        dialog = EncEditTargetDialog()
        response = dialog.run()

        if response != gtk.ResponseType.OK:
            dialog.destroy()
            return

        local = dialog.local_entry.get_text()
        remote = dialog.remote_entry.get_text()

        GlobalState.encsync.targets.append({"local": local, "remote": remote})
        self.target_list.update()
        GlobalState.file_viewer.refresh()

        dialog.destroy()

    def edit_limits_handler(self, widget):
        dialog = EncEditSpeedLimitDialog()

        response = dialog.run()

        if response != gtk.ResponseType.OK:
            dialog.destroy()
            return

        while not dialog.validate():
            response = dialog.run()

            if response != gtk.ResponseType.OK:
                dialog.destroy()
                return

        GlobalState.encsync.download_limit = dialog.get_download_limit()
        GlobalState.encsync.upload_limit = dialog.get_upload_limit()
        GlobalState.downloader.set_speed_limit(GlobalState.encsync.download_limit)
        GlobalState.synchronizer.set_speed_limit(GlobalState.encsync.upload_limit)

        dialog.destroy()

    def edit_n_threads_handler(self, widget):
        dialog = EncEditNumThreadsDialog()

        response = dialog.run()

        if response != gtk.ResponseType.OK:
            dialog.destroy()
            return

        while not dialog.validate():
            response = dialog.run()

            if response != gtk.ResponseType.OK:
                dialog.destroy()
                return

        GlobalState.encsync.download_threads = dialog.get_n_downloader_threads()
        GlobalState.encsync.sync_threads = dialog.get_n_synchronizer_threads()
        GlobalState.encsync.scan_threads = dialog.get_n_scanner_threads()

        dialog.destroy()

    def edit_key_handler(self, widget):
        dialog = EncEditKeyDialog()
        response = dialog.run()

        if response != gtk.ResponseType.OK:
            dialog.destroy()
            return

        new_key = dialog.entry.get_text()

        GlobalState.encsync.set_key(new_key)

        dialog.destroy()

    def edit_master_key_handler(self, widget):
        dialog = EncEditMasterKeyDialog()
        response = dialog.run()

        if response != gtk.ResponseType.OK:
            dialog.destroy()
            return

        while dialog.entry.get_text() != dialog.confirm_entry.get_text():
            response = dialog.run()
            if response != gtk.ResponseType.OK:
                dialog.destroy()
                return

        new_master_key = dialog.entry.get_text()
        GlobalState.encsync.set_master_key(new_master_key)
        dialog.destroy()
