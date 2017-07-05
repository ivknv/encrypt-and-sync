#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from .FileList import FileList
from .. import Paths
from .. import CentDB
from ..Node import normalize_node, node_tuple_to_dict, format_timestamp

def escape_glob(s):
    return "".join("[" + i + "]" if i in "*?[]" else i for i in s)

class LocalFileList(FileList):
    def __init__(self, directory=None, *args, **kwargs):
        FileList.__init__(self)

        kwargs.setdefault("isolation_level", None)

        if directory is None:
            path = "local_filelist.db"
        else:
            path = os.path.join(directory, "local_filelist.db")

        self.conn = CentDB.connect(path, *args, **kwargs)

    def time_since_last_commit(self):
        return self.conn.time_since_last_commit()

    def __enter__(self):
        self.conn.__enter__()

    def __exit__(self, *args, **kwargs):
        self.conn.__exit__()

    def create(self):
        with self.conn:
            self.conn.execute("""CREATE TABLE IF NOT EXISTS filelist
                                (type TEXT,
                                 modified DATETIME,
                                 padded_size INTEGER,
                                 path TEXT UNIQUE ON CONFLICT REPLACE)""")
            self.conn.execute("""CREATE INDEX IF NOT EXISTS path_index
                                ON filelist(path ASC)""")

    def insert_node(self, node):
        node = dict(node)
        normalize_node(node, True)

        self.conn.execute("""INSERT INTO filelist VALUES
                             (?, ?, ?, ?)""",
                          (node["type"],
                           format_timestamp(node["modified"]),
                           node["padded_size"],
                           node["path"]))

    def update_size(self, path, new_size):
        self.conn.execute("""UPDATE filelist SET padded_size=? WHERE path=?""",
                          (new_size, path))

    def remove_node(self, path):
        path = Paths.from_sys(path)
        self.conn.execute("""DELETE FROM filelist WHERE path=? OR path=?""",
                          (path, Paths.dir_normalize(path)))

    def remove_node_children(self, path):
        path = Paths.from_sys(path)
        path = Paths.dir_normalize(path)
        path = escape_glob(path)

        self.conn.execute("DELETE FROM filelist WHERE path GLOB ?",
                          (path + "*",))

    def clear(self):
        self.conn.execute("""DELETE FROM filelist""")

    def find_node(self, path):
        path = Paths.from_sys(path)
        with self.conn:
            self.conn.execute("""SELECT * FROM filelist
                                 WHERE path=? OR path=? LIMIT 1""",
                              (path, Paths.dir_normalize(path)))
            return node_tuple_to_dict(self.conn.fetchone())

    def find_node_children(self, path):
        path = Paths.from_sys(path)
        path = escape_glob(path)
        path_n = Paths.dir_normalize(path)

        with self.conn:
            self.conn.execute("""SELECT * FROM filelist
                                 WHERE path GLOB ? OR path=? OR path=?
                                 ORDER BY path ASC""",
                              (path_n + "*", path_n, path))
            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def select_all_nodes(self):
        with self.conn:
            self.conn.execute("""SELECT * FROM filelist ORDER BY path ASC""")

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def begin_transaction(self, *args, **kwargs):
        self.conn.begin_transaction(*args, **kwargs)

    def commit(self):
        self.conn.commit()

    def seamless_commit(self):
        self.conn.seamless_commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()
