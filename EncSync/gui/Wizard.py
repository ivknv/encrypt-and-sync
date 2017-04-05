#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject

from ..EncSync import EncSync, AUTH_URL

class EncWizard(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self, spacing=5)

        self.label = gtk.Label(label="Go to the following URL:")
        self.url_entry = gtk.Entry(text=AUTH_URL, editable=False)
        
        self.ynd_code_entry = gtk.Entry(placeholder_text="Confirmation code")
        self.master_key_entry = gtk.Entry(placeholder_text="Master password",
                                          visibility=False)
        self.master_key_confirm_entry = gtk.Entry(placeholder_text="Confirm master password",
                                                  visibility=False)
        self.key_entry = gtk.Entry(placeholder_text="Key", visibility=False)

        self.show_key_checkbox = gtk.CheckButton(label="Show key")
        self.show_key_checkbox.set_active(False)

        self.show_key_checkbox.connect("toggled", self.show_key_handler)

        self.error_message = gtk.Label(xalign=0.0)
        self.proceed_button = gtk.Button(label="Proceed")

        self.proceed_button.connect("clicked", self.proceed_handler)

        self.pack_start(self.label, False, True, 0)
        self.pack_start(self.url_entry, False, True, 0)
        self.pack_start(self.ynd_code_entry, False, True, 0)
        self.pack_start(self.master_key_entry, False, True, 0)
        self.pack_start(self.master_key_confirm_entry, False, True, 0)
        self.pack_start(self.key_entry, False, True, 0)
        self.pack_start(self.show_key_checkbox, False, True, 0)
        self.pack_start(self.error_message, False, True, 0)
        self.pack_start(self.proceed_button, False, True, 0)

        self.show_all()

    def show_key_handler(self, widget):
        if widget.get_active():
            self.key_entry.set_visibility(True)
        else:
            self.key_entry.set_visibility(False)

    def proceed_handler(self, widget):
        self.error_message.set_label("")

        if not self.confirm_master_key():
            return

        e = EncSync(self.get_master_key())

        response = e.ynd.get_token(self.get_code(), max_retries=0)

        if not response["success"]:
            self.error_message.set_label("Failed to get token. Try again")
            return
        else:
            token = response["data"]["access_token"]

        e.set_token(token)
        e.set_key(self.get_key())
        e.store_config("config.json")

        self.emit("setup-completed")

    def get_code(self):
        return self.ynd_code_entry.get_text()

    def get_master_key(self):
        return self.master_key_entry.get_text()

    def confirm_master_key(self):
        return self.master_key_confirm_entry.get_text() == self.get_master_key()

    def get_key(self):
        return self.key_entry.get_text()

    @staticmethod
    def register():
        gobject.type_register(EncWizard)
        gobject.signal_new("setup-completed", EncWizard, gobject.SIGNAL_RUN_FIRST,
                            gobject.TYPE_NONE, tuple())
