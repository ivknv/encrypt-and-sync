#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Downloader import Downloader, DownloadTarget
from ..Synchronizer import Synchronizer
from ..Scanner import Scanner
from .. import SyncList

from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject
from gi.repository import GLib as glib
from .. import paths

encsync = None
window = None
downloader = None
downloads = gtk.ListStore(int, str, str, str, str, gobject.TYPE_PYOBJECT)
synchronizer = None
sync_targets = gtk.ListStore(int, str, str, str, str, str, gobject.TYPE_PYOBJECT)
scanner = None
scan_tasks = gtk.ListStore(str, str, str, gobject.TYPE_PYOBJECT)
difflist = None

def wrap_ret(f, v):
    def g(*args, **kwargs):
        f(*args, **kwargs)
        return v
    return g

def initialize(esync):
    global encsync
    encsync = esync

    global downloader
    downloader = Downloader(encsync, n_workers=encsync.download_threads)
    downloader.set_speed_limit(encsync.download_limit)

    global synchronizer
    synchronizer = Synchronizer(encsync, n_workers=encsync.sync_threads)
    synchronizer.set_speed_limit(encsync.upload_limit)

    global scanner
    scanner = Scanner(encsync)

    global difflist
    difflist = SyncList.DiffList(encsync)
    with difflist:
        difflist.create()
        difflist.commit()

def finalize():
    t = (scanner, downloader, synchronizer)

    for i in t:
        if i is not None and i.is_alive():
            i.change_status("suspended")
            i.full_stop()

    for i in t:
        if i is not None and i.is_alive():
            i.join()

    if difflist is not None:
        difflist.close()

def show_error(message, secondary_message=""):
    dialog = gtk.MessageDialog(window, 0, gtk.MessageType.ERROR,
                               gtk.ButtonsType.OK, message)

    dialog.format_secondary_text(secondary_message)
    
    dialog.run()
    dialog.destroy()

def add_download(target_type, remote_path, IVs, local_path, prefix):
    remote_path = paths.join(prefix, remote_path)
    remote_path_enc, IVs = encsync.encrypt_path(remote_path, prefix, IVs)
    target = DownloadTarget()
    target.type = target_type
    target.remote = remote_path_enc
    target.local = local_path
    target.prefix = prefix
    target.IVs = IVs

    downloader.add_target(target)

    row = (0, str(target.status).capitalize(), remote_path, local_path, remote_path_enc, target)

    glib.idle_add(wrap_ret(downloads.append, False), row)

    return target

def add_sync_target(remote_path, local_path, status="pending"):
    remote_path_enc = encsync.encrypt_path(remote_path)[0]

    local_path = paths.from_sys(local_path)

    task = synchronizer.add_target(local_path, remote_path, status)

    row = (0, str(task.status).capitalize(), "None", remote_path, local_path, remote_path_enc, task)

    glib.idle_add(wrap_ret(sync_targets.append, False), row)

    return task

def add_scan_task(scan_type, path):
    task = scanner.add_dir(scan_type, path)

    row = (str(task.status).capitalize(), scan_type.capitalize(), path, task)

    glib.idle_add(wrap_ret(scan_tasks.append, False), row)

    return task
