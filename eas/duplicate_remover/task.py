# -*- coding: utf-8 -*-

from ..task import Task
from ..filelist import Filelist
from .. import pathm

__all__ = ["DuplicateRemoverTask"]

class DuplicateRemoverTask(Task):
    def __init__(self, target):
        Task.__init__(self)

        self.parent = target
        self.config = target.config
        self.path = None
        self.ivs = None
        self.prefix = None
        self.filename_encoding = None
        self.storage = None
        self.duplist = target.shared_duplist

    def autocommit(self):
        self.parent.autocommit()

    def complete(self):
        try:
            if self.stopped:
                return True

            self.status = "pending"

            encoding = self.filename_encoding
            encpath = self.config.encrypt_path(self.path, self.prefix,
                                               IVs=self.ivs,
                                               filename_encoding=encoding)[0]

            if self.parent.preserve_modified and self.storage.supports_set_modified:
                if not pathm.is_equal(self.path, self.prefix):
                    folder = self.config.identify_folder(self.storage.name, self.path)

                    if folder is not None:
                        filelist = Filelist(folder["name"], self.parent.duprem.directory)
                        parent_modified = filelist.find(pathm.split(self.path)[0])["modified"]
                    else:
                        parent_modified = None

                    if not parent_modified:
                        try:
                            parent_modified = self.storage.get_meta(pathm.split(encpath)[0])["modified"]
                        except FileNotFoundError:
                            parent_modified = None

            try:
                self.storage.remove(encpath)
                removed = True
            except FileNotFoundError:
                removed = False

            self.duplist.remove(self.ivs, self.path)

            self.autocommit()

            # Preserve parent modified date
            if self.parent.preserve_modified and self.path not in ("", "/") and removed:
                if self.storage.supports_set_modified and parent_modified is not None:
                    self.storage.set_modified(pathm.dirname(encpath), parent_modified)

            self.status = "finished"
        except KeyboardInterrupt:
            return
