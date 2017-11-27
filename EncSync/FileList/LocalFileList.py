#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .FileList import FileList
from .. import Paths
from ..common import normalize_node, node_tuple_to_dict, format_timestamp
from ..common import escape_glob, validate_target_name

class LocalFileList(FileList):
    def __init__(self, name, directory=None, *args, **kwargs):
        if not validate_target_name(name):
            raise ValueError("Invalid target name: %r" % (name,))

        FileList.__init__(self, "%s-local.db" % (name,), directory, *args, **kwargs)

    def create(self):
        with self.connection:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS filelist
                                       (type TEXT,
                                        modified DATETIME,
                                        padded_size INTEGER,
                                        path TEXT UNIQUE ON CONFLICT REPLACE)""")
            self.connection.execute("""CREATE INDEX IF NOT EXISTS path_index
                                       ON filelist(path ASC)""")

    def get_root(self):
        """
            Get the root node which is also the target prefix.

            :returns: `dict`
        """

        with self.connection:
            self.connection.execute("SELECT * FROM filelist ORDER BY path ASC LIMIT 1")
            return node_tuple_to_dict(self.connection.fetchone())

    def insert_node(self, node):
        node = dict(node)
        normalize_node(node, True)

        if node["type"] is None:
            raise ValueError("Node type must not be None")

        self.connection.execute("INSERT INTO filelist VALUES (?, ?, ?, ?)",
                                (node["type"],
                                 format_timestamp(node["modified"]),
                                 node["padded_size"],
                                 node["path"]))

    def update_size(self, path, new_size):
        self.connection.execute("UPDATE filelist SET padded_size=? WHERE path=?",
                                (new_size, path))

    def remove_node(self, path):
        path = Paths.from_sys(path)
        self.connection.execute("DELETE FROM filelist WHERE path=? OR path=?",
                                (path, Paths.dir_normalize(path)))

    def remove_node_children(self, path):
        path = Paths.from_sys(path)
        path = Paths.dir_normalize(path)
        path = escape_glob(path)

        self.connection.execute("DELETE FROM filelist WHERE path GLOB ?",
                                (path + "*",))

    def clear(self):
        self.connection.execute("DELETE FROM filelist")

    def find_node(self, path):
        path = Paths.from_sys(path)
        with self.connection:
            self.connection.execute("""SELECT * FROM filelist
                                       WHERE path=? OR path=? LIMIT 1""",
                                    (path, Paths.dir_normalize(path)))
            return node_tuple_to_dict(self.connection.fetchone())

    def find_node_children(self, path):
        path = Paths.from_sys(path)
        path = escape_glob(path)
        path_n = Paths.dir_normalize(path)

        with self.connection:
            self.connection.execute("""SELECT * FROM filelist
                                       WHERE path GLOB ? OR path=? OR path=?
                                       ORDER BY path ASC""",
                                    (path_n + "*", path_n, path))
            return (node_tuple_to_dict(i) for i in self.connection.genfetch())

    def select_all_nodes(self):
        with self.connection:
            self.connection.execute("SELECT * FROM filelist ORDER BY path ASC")

            return (node_tuple_to_dict(i) for i in self.connection.genfetch())
