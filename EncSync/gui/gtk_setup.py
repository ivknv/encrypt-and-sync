#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk as gtk

WIDGET_CLASS_MAP = {"label": gtk.Label, "entry": gtk.Entry}

def gtk_setup(definition):
    if isinstance(definition, dict):
        return match_setup(definition)

    return setup_iterable(definition)

def setup_iterable(definitions):
    for i in definitions:
        gtk_setup(i)

def setup_default(definition):
    widget = definition.get("object", None)

    if widget is None:
        widget = WIDGET_CLASS_MAP[definition["type"].lower()]()
        definition["object"] = widget

    set_properties(definition)

def setup_treeview(definition):
    widget = definition.get("object", None)

    if widget is None:
        widget = gtk.TreeView()
        definition["object"] = widget

    model = widget.get_model()

    if model is None:
        model = definition["model"]

    widget.set_model(model)

    for i in definition["columns"]:
        setup_treeview_column(i)
        widget.append_column(i["object"])

def setup_treeview_column(definition):
    RENDERER_ATTR_MAP = {"text": "text", "toggle": "active"}

    col = definition.get("object", None)

    if col is None:
        col = gtk.TreeViewColumn()
        definition["object"] = col

    set_properties(definition)

    for i in definition["renderers"]:
        setup_cell_renderer(i)

        renderer = i["object"]
        attr = RENDERER_ATTR_MAP[i["type"].lower()]
        idx = i["index"]

        col.pack_start(renderer, i["expand"])
        col.add_attribute(renderer, attr, idx)

def setup_cell_renderer(definition):
    RENDERER_CLASSES = {"text": gtk.CellRendererText,
                        "toggle": gtk.CellRendererToggle}

    renderer = definition.get("object", None)

    if renderer is None:
        renderer = RENDERER_CLASSES[definition["type"].lower()]()
        definition["object"] = renderer

    set_properties(definition)

def setup_dialog(definition):
    dialog = definition.get("object", None)

    if dialog is None:
        dialog = gtk.Dialog()

    buttons = definition.get("buttons", [])

    for text, response in zip(buttons[::2], buttons[1::2]):
        dialog.add_button(text, response)

    set_properties(definition)

    box = dialog.get_content_area()

    for i in definition.get("children", []):
        setup_pack_start(box, i)

def setup_pack_start(parent, definition):
    match_setup(definition)

    parent.pack_start(definition["object"], definition["expand"],
                      definition["fill"], definition.get("padding", 0))

def match_setup(definition):
    SETUP_MAP = {"treeview": setup_treeview,
                 "dialog": setup_dialog}

    return SETUP_MAP.get(definition["type"].lower(), setup_default)(definition)

def set_properties(definition):
    obj = definition.get("object", None)

    if obj is None:
        return

    properties = definition.get("properties", {})

    for prop, value in properties.items():
        obj.set_property(prop, value)
