#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .FileList import FileList
from .. import paths
from .. import CentDB
from ..Node import normalize_node, node_tuple_to_dict, format_timestamp

class RemoteFileList(FileList):
    def __init__(self, *args, **kwargs):
        FileList.__init__(self)
        kwargs.setdefault("isolation_level", None)
        path = "remote_filelist.db"
        self.conn = CentDB.connect(path, *args, **kwargs)

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
                           node["path"],
                           node["IVs"]))

    def remove_node(self, path):
        self.conn.execute("""DELETE FROM filelist WHERE path=? OR path=?""",
                          (path, paths.dir_normalize(path)))

    def remove_node_children(self, path):
        path = paths.dir_normalize(path)

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
                              (path, paths.dir_normalize(path)))
            return node_tuple_to_dict(self.conn.fetchone())

    def find_node_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT * FROM filelist
                                WHERE path LIKE ? ESCAPE '\\' ORDER BY path ASC""",
                              (path + "%",))

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def select_all_nodes(self):
        with self.conn:
            self.conn.execute("""SELECT * FROM filelist ORDER BY path ASC""")

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def is_empty(self, parent_dir="/"):
        parent_dir = paths.dir_normalize(parent_dir)

        parent_dir = parent_dir.replace("%", "\\%")
        parent_dir = parent_dir.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM filelist
                                 WHERE path LIKE ? ESCAPE '\\' LIMIT 1""",
                              (parent_dir + "%",))

            return self.conn.fetchone()[0] == 0

    def get_file_count(self, parent_dir="/"):
        parent_dir = paths.dir_normalize(parent_dir)

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

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()
