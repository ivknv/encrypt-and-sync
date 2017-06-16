#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from .FileList import FileList
from .. import Paths
from .. import CentDB
from ..Node import normalize_node, node_tuple_to_dict, format_timestamp

def prepare_path(path):
    return Paths.join_properly("/", path)

class RemoteFileList(FileList):
    def __init__(self, directory=None, *args, **kwargs):
        FileList.__init__(self)

        kwargs.setdefault("isolation_level", None)
        if directory is None:
            path = "remote_filelist.db"
        else:
            path = os.path.join(directory, "remote_filelist.db")

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
                                 path TEXT UNIQUE ON CONFLICT REPLACE,
                                 IVs TEXT)""")
            self.conn.execute("""CREATE INDEX IF NOT EXISTS path_index
                                 ON filelist(path ASC)""")

    def insert_node(self, node):
        node = dict(node)
        normalize_node(node, False)

        self.conn.execute("""INSERT INTO filelist VALUES
                            (?, ?, ?, ?, ?)""",
                          (node["type"],
                           format_timestamp(node["modified"]),
                           node["padded_size"],
                           prepare_path(node["path"]),
                           node["IVs"]))

    def remove_node(self, path):
        path = prepare_path(path)

        self.conn.execute("""DELETE FROM filelist WHERE path=? OR path=?""",
                          (path, Paths.dir_normalize(path)))

    def remove_node_children(self, path):
        path = prepare_path(Paths.dir_normalize(path))

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        self.conn.execute("DELETE FROM filelist WHERE path LIKE ? ESCAPE '\\'",
                          (path + "%",))

    def clear(self):
        self.conn.execute("""DELETE FROM filelist""")

    def find_node(self, path):
        path = prepare_path(path)

        with self.conn:
            self.conn.execute("""SELECT * FROM filelist
                                 WHERE path=? OR path=? LIMIT 1""",
                              (path, Paths.dir_normalize(path)))
            return node_tuple_to_dict(self.conn.fetchone())

    def find_node_children(self, path):
        path = prepare_path(path)
        path_n = Paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")
        path_n = path_n.replace("%", "\\%")
        path_n = path_n.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT * FROM filelist
                                WHERE path LIKE ? ESCAPE '\\'
                                      OR path=? OR path=? ORDER BY path ASC""",
                              (path_n + "%", path, path_n))

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def select_all_nodes(self):
        with self.conn:
            self.conn.execute("""SELECT * FROM filelist ORDER BY path ASC""")

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def is_empty(self, parent_dir="/"):
        parent_dir = prepare_path(Paths.dir_normalize(parent_dir))

        parent_dir = parent_dir.replace("%", "\\%")
        parent_dir = parent_dir.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM filelist
                                 WHERE path LIKE ? ESCAPE '\\' LIMIT 1""",
                              (parent_dir + "%",))

            return self.conn.fetchone()[0] == 0

    def get_file_count(self, parent_dir="/"):
        parent_dir = prepare_path(Paths.dir_normalize(parent_dir))

        parent_dir = parent_dir.replace("%", "\\%")
        parent_dir = parent_dir.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM filelist
                                 WHERE path LIKE ? ESCAPE '\\'""",
                              (parent_dir + "%",))

            return self.conn.fetchone()[0]

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
