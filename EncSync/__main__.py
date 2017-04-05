#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject

from .gui.LoginForm import LoginForm
from .gui.Viewer import EncViewer
from .gui.Wizard import EncWizard
from .gui import GlobalState

class EncWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self, title="EncSync")

        self.connect("delete-event", self.window_close_handler)
        self.connect("delete-event", gtk.main_quit)

        self.set_default_size(640, 480)
        self.set_border_width(10)

        self.viewer = EncViewer()

        GlobalState.window = self

        if not os.path.exists("config.json"):
            self.show_setup_wizard()
        else:
            self.show_viewer()

    def show_viewer(self):
        for i in self.get_children():
            self.remove(i)

        self.add(self.viewer)

        self.show_all()

    def show_setup_wizard(self):
        wizard = EncWizard()

        wizard.connect("setup-completed", lambda widget: self.show_viewer())

        self.add(wizard)

        self.show_all()

    def window_close_handler(self, widget, *args, **kwargs):
        GlobalState.finalize()

        return False

if __name__ == "__main__":
    gobject.threads_init()

    LoginForm.register()
    EncWizard.register()
    window = EncWindow()
    window.show_all()
    gtk.main()
