#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from .. import Paths
from .. import CentDB

def prepare_path(path):
    return Paths.join_properly("/", path)

def escape_glob(s):
    return "".join("[" + i + "]" if i in "*?[]" else i for i in s)

class DuplicateList(object):
    def __init__(self, directory=None, *args, **kwargs):
        kwargs.setdefault("isolation_level", None)

        if directory is None:
            path = "duplicates.db"
        else:
            path = os.path.join(directory, "duplicates.db")

        self.conn = CentDB.connect(path, *args, **kwargs)

    def __enter__(self):
        self.conn.__enter__()

    def __exit__(self, *args, **kwargs):
        self.conn.__exit__(*args, **kwargs)

    def create(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS duplicates
                             (type TEXT,
                              IVs TEXT,
                              path TEXT)""")

    def insert(self, node_type, IVs, path):
        path = prepare_path(path)

        self.conn.execute("INSERT INTO duplicates VALUES (?, ?, ?)",
                          (node_type, IVs, path))

    def remove(self, IVs, path):
        path = prepare_path(path)

        self.conn.execute("DELETE FROM duplicates WHERE (path=? OR path=?) AND IVs=?",
                          (path, Paths.dir_normalize(path), IVs))

    def remove_children(self, path):
        path = prepare_path(Paths.dir_normalize(path))
        path = escape_glob(path)

        self.conn.execute("DELETE FROM duplicates WHERE path GLOB ?", (path + "*",))

    def clear(self):
        self.conn.execute("DELETE FROM duplicates")

    def find(self, IVs, path):
        path = prepare_path(path)

        with self.conn:
            self.conn.execute("""SELECT * FROM duplicates
                                 WHERE IVs=? AND (path=? OR path=?) LIMIT 1""",
                              (IVs, path, Paths.dir_normalize(path)))
            return self.conn.fetchone()

    def find_children(self, path):
        path = prepare_path(Paths.dir_normalize(path))
        path = escape_glob(path)

        with self.conn:
            self.conn.execute("""SELECT * FROM duplicates WHERE path GLOB ?""",
                              (path + "*",))

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
        path = prepare_path(Paths.dir_normalize(path))
        path = escape_glob(path)

        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM
                                 (SELECT * FROM duplicates
                                  WHERE path GLOB ? LIMIT 1)""",
                              (path + "*",))
            return self.conn.fetchone()[0] == 0

    def begin_transaction(self, *args, **kwargs):
        self.conn.begin_transaction(*args, **kwargs)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()
