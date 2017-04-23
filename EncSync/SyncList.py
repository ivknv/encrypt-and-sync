#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import paths
from . import CentDB
from .Node import normalize_node, node_tuple_to_dict, format_timestamp

class SyncList(object):
    def __init__(self, path=None, *args, **kwargs):
        if path is None:
            path = "encsync.db"
        kwargs.setdefault("isolation_level", None)
        self.conn = CentDB.connect(path, *args, **kwargs)

    def __enter__(self):
        self.conn.__enter__()

    def __exit__(self, *args, **kwargs):
        self.conn.__exit__()

    def create(self):
        with self.conn:
            self.conn.execute("""CREATE TABLE IF NOT EXISTS local_filelist
                                (type TEXT,
                                 modified DATETIME,
                                 padded_size INTEGER,
                                 path TEXT UNIQUE ON CONFLICT REPLACE)""")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS remote_filelist
                                (type TEXT,
                                 modified DATETIME,
                                 padded_size INTEGER,
                                 path TEXT UNIQUE ON CONFLICT REPLACE,
                                 IVs TEXT)""")
            self.conn.execute("""CREATE INDEX IF NOT EXISTS local_path_index
                                ON local_filelist(path ASC)""")
            self.conn.execute("""CREATE INDEX IF NOT EXISTS remote_path_index
                                ON remote_filelist(path ASC)""")

    def insert_local_node(self, node):
        node = dict(node)
        normalize_node(node, True)

        self.conn.execute("""INSERT INTO local_filelist VALUES
                             (?, ?, ?, ?)""",
                          (node["type"],
                           format_timestamp(node["modified"]),
                           node["padded_size"],
                           node["path"]))

    def update_local_size(self, path, new_size):
        self.conn.execute("""UPDATE local_filelist
                             SET padded_size=? WHERE path=?""",
                          (new_size, path))

    def insert_remote_node(self, node):
        node = dict(node)
        normalize_node(node, False)

        self.conn.execute("""INSERT INTO remote_filelist VALUES
                            (?, ?, ?, ?, ?)""",
                          (node["type"],
                           format_timestamp(node["modified"]),
                           node["padded_size"],
                           node["path"],
                           node["IVs"]))

    def remove_remote_node(self, path):
        self.conn.execute("""DELETE FROM remote_filelist
                             WHERE path=? OR path=?""",
                          (path, paths.dir_normalize(path)))

    def remove_remote_node_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        self.conn.execute("DELETE FROM remote_filelist WHERE path LIKE ? ESCAPE '\\'",
                          (path + "%",))

    def remove_local_node(self, path):
        self.conn.execute("""DELETE FROM local_filelist
                             WHERE path=? OR path=?""",
                          (path, paths.dir_normalize(path)))

    def remove_local_node_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        self.conn.execute("DELETE FROM local_filelist WHERE path LIKE ? ESCAPE '\\'",
                          (path + "%",))

    def clear_local(self):
        self.conn.execute("""DELETE FROM local_filelist""")

    def clear_remote(self):
        self.conn.execute("""DELETE FROM remote_filelist""")

    def find_local_node(self, path):
        with self.conn:
            self.conn.execute("""SELECT * FROM local_filelist
                                 WHERE path=? OR path=? LIMIT 1""",
                              (path, paths.dir_normalize(path)))
            return node_tuple_to_dict(self.conn.fetchone())

    def find_remote_node(self, path):
        with self.conn:
            self.conn.execute("""SELECT * FROM remote_filelist
                                 WHERE path=? OR path=? LIMIT 1""",
                              (path, paths.dir_normalize(path)))
            return node_tuple_to_dict(self.conn.fetchone())

    def find_local_node_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT * FROM local_filelist
                                WHERE path LIKE ? ESCAPE '\\' ORDER BY path ASC""",
                              (path + "%",))

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def find_remote_node_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT * FROM remote_filelist
                                WHERE path LIKE ? ESCAPE '\\' ORDER BY path ASC""",
                              (path + "%",))

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def select_all_local_nodes(self):
        with self.conn:
            self.conn.execute("""SELECT * FROM local_filelist ORDER BY path ASC""")

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def select_all_remote_nodes(self):
        with self.conn:
            self.conn.execute("""SELECT * FROM remote_filelist ORDER BY path ASC""")

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def insert_local_nodes(self, nodes):
        with self.conn:
            for i in nodes:
                self.insert_local_node(i)

    def insert_remote_nodes(self, nodes):
        with self.conn:
            for i in nodes:
                self.insert_remote_node(i)

    def is_remote_list_empty(self, parent_dir="/"):
        parent_dir = paths.dir_normalize(parent_dir)

        parent_dir = parent_dir.replace("%", "\\%")
        parent_dir = parent_dir.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM remote_filelist
                                 WHERE path LIKE ? ESCAPE '\\' LIMIT 1""",
                              (parent_dir + "%",))

            return self.conn.fetchone()[0] == 0

    def get_remote_file_count(self, parent_dir="/"):
        parent_dir = paths.dir_normalize(parent_dir)

        parent_dir = parent_dir.replace("%", "\\%")
        parent_dir = parent_dir.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM remote_filelist
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
