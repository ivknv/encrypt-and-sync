#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .FileList import FileList
from .. import Paths
from .. import CentDB
from ..Node import normalize_node, node_tuple_to_dict, format_timestamp

class LocalFileList(FileList):
    def __init__(self, *args, **kwargs):
        FileList.__init__(self)

        kwargs.setdefault("isolation_level", None)
        path = "local_filelist.db"

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
        self.conn.execute("""DELETE FROM filelist WHERE path=? OR path=?""",
                          (path, Paths.dir_normalize(path)))

    def remove_node_children(self, path):
        path = Paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        self.conn.execute("DELETE FROM filelist WHERE path LIKE ? ESCAPE '\\'",
                          (path + "%",))

    def clear(self):
        self.conn.execute("""DELETE FROM filelist""")

    def find_node(self, path):
        with self.conn:
            self.conn.execute("""SELECT * FROM filelist
                                 WHERE path=? OR path=? LIMIT 1""",
                              (path, Paths.dir_normalize(path)))
            return node_tuple_to_dict(self.conn.fetchone())

    def find_node_children(self, path):
        path_n = Paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")
        path_n = path_n.replace("%", "\\%")
        path_n = path_n.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT * FROM filelist
                                 WHERE path LIKE ? ESCAPE '\\'
                                       OR path=? OR path=? ORDER BY path ASC""",
                              (path_n + "%", path_n, path))

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def select_all_nodes(self):
        with self.conn:
            self.conn.execute("""SELECT * FROM filelist ORDER BY path ASC""")

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def begin_transaction(self, *args, **kwargs):
        self.conn.begin_transaction(*args, **kwargs)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()
