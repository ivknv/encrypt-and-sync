#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import Paths
from ..common import escape_glob

from .BaseFileList import BaseFileList

__all__ = ["DuplicateList"]

def prepare_path(path):
    return Paths.join_properly("/", path)

class DuplicateList(BaseFileList):
    def __init__(self, storage_name, directory=None, filename=None, *args, **kwargs):
        if filename is None:
            filename = "%s-duplicates.db" % (storage_name,)

        BaseFileList.__init__(self, filename, directory, *args, **kwargs)

    def create(self):
        self.connection.execute("""CREATE TABLE IF NOT EXISTS duplicates
                                   (type TEXT,
                                    IVs TEXT,
                                    path TEXT)""")

    def insert(self, node_type, IVs, path):
        path = prepare_path(path)

        self.connection.execute("INSERT INTO duplicates VALUES (?, ?, ?)",
                                (node_type, IVs, path))

    def remove(self, IVs, path):
        path = prepare_path(path)

        self.connection.execute("DELETE FROM duplicates WHERE (path=? OR path=?) AND IVs=?",
                          (path, Paths.dir_normalize(path), IVs))

    def remove_children(self, path):
        path = prepare_path(Paths.dir_normalize(path))
        path = escape_glob(path)

        self.connection.execute("DELETE FROM duplicates WHERE path GLOB ?", (path + "*",))

    def clear(self):
        self.connection.execute("DELETE FROM duplicates")

    def find(self, IVs, path):
        path = prepare_path(path)

        with self.connection:
            self.connection.execute("""SELECT * FROM duplicates
                                       WHERE IVs=? AND (path=? OR path=?) LIMIT 1""",
                                    (IVs, path, Paths.dir_normalize(path)))
            return self.connection.fetchone()

    def find_children(self, path):
        path = prepare_path(Paths.dir_normalize(path))
        path = escape_glob(path)

        with self.connection:
            self.connection.execute("SELECT * FROM duplicates WHERE path GLOB ?",
                                    (path + "*",))

            return self.connection.genfetch()

    def select_all(self):
        with self.connection:
            self.connection.execute("""SELECT * FROM duplicates""")

            return self.connection.genfetch()

    def get_count(self):
        with self.connection:
            self.connection.execute("SELECT COUNT(*) FROM duplicates")
            return self.connection.fetchone()[0]

    def get_children_count(self, path):
        path = prepare_path(Paths.dir_normalize(path))
        path = escape_glob(path)

        with self.connection:
            self.connection.execute("SELECT COUNT(*) FROM duplicates WHERE path GLOB ?",
                                    (path + "*",))

            return self.connection.fetchone()[0]

    def is_empty(self, path="/"):
        path = prepare_path(Paths.dir_normalize(path))
        path = escape_glob(path)

        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM
                                       (SELECT * FROM duplicates
                                        WHERE path GLOB ? LIMIT 1)""",
                                    (path + "*",))
            return self.connection.fetchone()[0] == 0
