#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from ..EncSync import EncSync, AUTH_URL
from . import GlobalState

import json

try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError

class EnterConfirmCodeDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self, "Enter confirmation code", GlobalState.window, 0,
                            (gtk.STOCK_OK, gtk.ResponseType.OK,
                             gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL))
        
        box = self.get_content_area()

        self.label = gtk.Label("Go to the following URL and enter the code: ", xalign=0.0)
        self.url_entry = gtk.Entry(text=AUTH_URL, editable=False)
        self.entry = gtk.Entry(placeholder_text="Confirmation code")
        self.error_message = gtk.Label()

        box.pack_start(self.label, False, True, 0)
        box.pack_start(self.url_entry, False, True, 0)
        box.pack_start(self.entry, False, True, 0)
        box.pack_start(self.error_message, False, True, 0)

        self.show_all()

    def get_code(self):
        return self.entry.get_text()

class LoginForm(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self, spacing=10)

        self.master_key_entry = gtk.Entry(visibility=False, placeholder_text="Master password")
        self.login_button = gtk.Button(label="Log in", xalign=0.0)
        self.entry_label = gtk.Label(label="Master password:", xalign=0.0)
        self.message_label = gtk.Label(label="", xalign=0.0)

        self.hbox = gtk.HBox()

        self.hbox.pack_start(self.login_button, False, True, 0)

        self.pack_start(self.entry_label, False, True, 0)
        self.pack_start(self.master_key_entry, False, True, 0)
        self.pack_start(self.hbox, False, True, 0)
        self.pack_start(self.message_label, False, True, 0)

        self.login_button.connect("clicked", self.login_handler)

        self.master_key_entry.connect("activate", self.on_activate)

    def on_activate(self, widget):
        self.login_button.emit("clicked")

    def get_token(self, encsync):
        dialog = EnterConfirmCodeDialog()

        try:
            while True:
                response = dialog.run()

                dialog.error_message.set_label("")

                if response != gtk.ResponseType.OK:
                    return

                r = encsync.ynd.get_token(dialog.get_code(), max_retries=0)

                if not r["success"]:
                    dialog.error_message.set_label("Failed to get token. Try again")
                else:
                    return r["data"]["access_token"]
        finally:
            dialog.destroy()

    def login_handler(self, button):
        self.message_label.set_label("")
        encsync = EncSync(self.master_key_entry.get_text())
        try:
            encsync.load_config("config.json")

            token_valid = encsync.check_token()

            if not token_valid:
                token = self.get_token(encsync)
                encsync.set_token(token)
                encsync.store_config("config.json")

            GlobalState.initialize(encsync)
            
            self.emit("login-completed")
        except (JSONDecodeError, UnicodeDecodeError) as e:
            self.message_label.set_label("Login failed")

    @staticmethod
    def register():
        gobject.type_register(LoginForm)
        gobject.signal_new("login-completed", LoginForm, gobject.SIGNAL_RUN_FIRST,
                            gobject.TYPE_NONE, tuple())
