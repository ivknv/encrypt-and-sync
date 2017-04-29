#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import paths
from .. import CentDB

class DuplicateList(object):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("isolation_level", None)

        path = "duplicates.db"

        self.conn = CentDB.connect(path, *args, **kwargs)

    def __enter__(self):
        self.conn.__enter__()

    def __exit__(self, *args, **kwargs):
        self.conn.__exit__(*args, **kwargs)

    def create(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS duplicates
                             (type TEXT,
                              path_enc TEXT UNIQUE ON CONFLICT REPLACE)""")

    def insert(self, node_type, path_enc):
        self.conn.execute("INSERT INTO duplicates VALUES (?, ?)",
                          (node_type, path_enc))

    def remove(self, path_enc):
        self.conn.execute("DELETE FROM duplicates WHERE path_enc=? OR path_enc=?",
                          (path_enc, paths.dir_normalize(path_enc)))

    def remove_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        self.conn.execute("DELETE FROM duplicates WHERE path_enc LIKE ? ESCAPE '\\'",
                          (path + "%",))

    def clear(self):
        self.conn.execute("DELETE FROM duplicates")

    def find(self, path_enc):
        with self.conn:
            self.conn.execute("""SELECT * FROM duplicates
                                 WHERE path_enc=? OR path_enc=? LIMIT 1""",
                              (path_enc, paths.dir_normalize(path_enc)))
            return self.conn.fetchone()

    def find_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT * FROM duplicates
                                 WHERE path_enc LIKE ? ESCAPE '\\'""",
                              (path + "%",))

            return self.conn.genfetch()

    def select_all(self):
        with self.conn:
            self.conn.execute("""SELECT * FROM duplicates""")

            return self.conn.genfetch()

    def get_count(self):
        with self.conn:
            self.conn.execute("SELECT COUNT(*) FROM duplicates")
            return self.conn.fetchone()[0]

    def is_empty(self, path="/"):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM
                                 (SELECT * FROM duplicates
                                  WHERE path_enc LIKE ? ESCAPE '\\' LIMIT 1)""",
                              (path + "%",))
            return self.conn.fetchone()[0] == 0

    def begin_transaction(self, *args, **kwargs):
        self.conn.begin_transaction(*args, **kwargs)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()
