#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .BaseFileList import BaseFileList
from .. import Paths
from ..common import node_tuple_to_dict, format_timestamp
from ..common import escape_glob, validate_folder_name, validate_storage_name

__all__ = ["FileList"]

def prepare_path(path):
    return Paths.join_properly("/", path)

class FileList(BaseFileList):
    def __init__(self, folder_name, directory=None, *args, **kwargs):
        if not validate_folder_name(folder_name):
            raise ValueError("Invalid folder name: %r" % (folder_name,))

        BaseFileList.__init__(self, "%s-filelist.db" % (folder_name,),
                              directory, *args, **kwargs)

    def create(self):
        with self.connection:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS filelist
                                       (type TEXT,
                                        modified DATETIME,
                                        padded_size INTEGER,
                                        path TEXT UNIQUE ON CONFLICT REPLACE,
                                        IVs TEXT)""")
            self.connection.execute("""CREATE INDEX IF NOT EXISTS path_index
                                       ON filelist(path ASC)""")
    def get_root(self):
        """
            Get the root node which is also the folder prefix.

            :returns: `dict`
        """

        with self.connection:
            self.connection.execute("SELECT * FROM filelist ORDER BY path ASC LIMIT 1")
            return node_tuple_to_dict(self.connection.fetchone())

    def insert_node(self, node):
        node = dict(node)
        if node["type"] == "d":
            node["path"] = Paths.dir_normalize(node["path"])

        if node["type"] is None:
            raise ValueError("Node type is None")

        self.connection.execute("""INSERT INTO filelist VALUES
                                   (?, ?, ?, ?, ?)""",
                                (node["type"],
                                 format_timestamp(node["modified"]),
                                 node["padded_size"],
                                 prepare_path(node["path"]),
                                 node["IVs"]))

    def remove_node(self, path):
        path = prepare_path(path)

        self.connection.execute("DELETE FROM filelist WHERE path=? OR path=?",
                                (path, Paths.dir_normalize(path)))

    def remove_node_children(self, path):
        path = prepare_path(Paths.dir_normalize(path))
        path = escape_glob(path)

        self.connection.execute("DELETE FROM filelist WHERE path GLOB ?", (path + "*",))

    def clear(self):
        self.connection.execute("DELETE FROM filelist")

    def find_node(self, path):
        path = prepare_path(path)

        with self.connection:
            self.connection.execute("""SELECT * FROM filelist
                                       WHERE path=? OR path=? LIMIT 1""",
                                    (path, Paths.dir_normalize(path)))
            return node_tuple_to_dict(self.connection.fetchone())

    def find_node_children(self, path):
        path = prepare_path(path)
        path = escape_glob(path)
        path_n = Paths.dir_normalize(path)

        with self.connection:
            self.connection.execute("""SELECT * FROM filelist
                                       WHERE path GLOB ? OR path=? OR path=?
                                       ORDER BY path ASC""",
                                    (path_n + "*", path, path_n))

            return (node_tuple_to_dict(i) for i in self.connection.genfetch())

    def select_all_nodes(self):
        with self.connection:
            self.connection.execute("SELECT * FROM filelist ORDER BY path ASC")

            return (node_tuple_to_dict(i) for i in self.connection.genfetch())

    def is_empty(self, parent_dir="/"):
        parent_dir = prepare_path(Paths.dir_normalize(parent_dir))
        parent_dir = escape_glob(parent_dir)

        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM filelist
                                       WHERE path GLOB ? LIMIT 1""",
                                    (parent_dir + "*",))

            return self.connection.fetchone()[0] == 0

    def get_file_count(self, path="/"):
        parent_dir = prepare_path(Paths.dir_normalize(path))
        parent_dir = escape_glob(path)

        with self.connection:
            self.connection.execute("SELECT COUNT(*) FROM filelist WHERE path GLOB ?",
                                    (parent_dir + "*",))

            return self.connection.fetchone()[0]

    def update_size(self, path, new_size):
        self.connection.execute("UPDATE filelist SET padded_size=? WHERE path=?",
                                (new_size, path))
