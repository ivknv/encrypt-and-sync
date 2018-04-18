#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import CDB

__all__ = ["DiffList"]

class DiffList(object):
    def __init__(self, directory=None, *args, **kwargs):
        if directory is None:
            path = "encsync_diffs.db"
        else:
            path = os.path.join(directory, "encsync_diffs.db")

        kwargs.setdefault("isolation_level", None)

        self.connection = CDB.connect(path, *args, **kwargs)

    def __enter__(self):
        self.connection.__enter__()

    def __exit__(self, *args, **kwargs):
        self.connection.__exit__()

    def create(self):
        with self.connection:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS differences
                                       (type TEXT, node_type TEXT,
                                        path TEXT, folder1 TEXT, folder2 TEXT)""")
            self.connection.execute("""CREATE INDEX IF NOT EXISTS differences_path_index
                                       ON differences(path ASC)""")

    def insert_difference(self, diff):
        diff_type = diff["type"]
        node_type = diff["node_type"]
        path = diff["path"]
        folder1 = diff["folder1"]
        folder2 = diff["folder2"]

        self.connection.execute("INSERT INTO differences VALUES (?, ?, ?, ?, ?)",
                                (diff_type, node_type, path, folder1, folder2))

    def clear_differences(self, folder1, folder2):
        self.connection.execute("""DELETE FROM differences WHERE
                                   folder1=? AND folder2=?""", (folder1, folder2))

    def fetch_differences(self):
        for i in self.connection.genfetch():
            yield {"type": i[0],
                   "node_type": i[1],
                   "path": i[2],
                   "folder1": i[3],
                   "folder2": i[4]}

    def select_rm_differences(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE type='rm' AND folder1=? AND folder2=?
                                       ORDER BY path ASC""", (folder1, folder2))
            return self.fetch_differences()

    def select_dirs_differences(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE type='new' AND node_type='d' AND
                                             folder1=? AND folder2=?
                                       ORDER BY path ASC""", (folder1, folder2))

            return self.fetch_differences()

    def count_dirs_differences(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE type='new' AND node_type='d' AND
                                             folder1=?  AND folder2=?""",
                                    (folder1, folder2))
            return self.connection.fetchone()[0]

    def count_files_differences(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE (type='new' OR type='update') AND
                                             node_type='f' AND folder1=?  AND folder2=?""",
                                    (folder1, folder2))
            return self.connection.fetchone()[0]

    def count_rm_differences(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE type='rm' AND folder1=? AND folder2=?""",
                                    (folder1, folder2))
            return self.connection.fetchone()[0]

    def count_new_file_differences(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE type='new' AND node_type='f' AND
                                             folder1=? AND folder2=?""",
                                    (folder1, folder2))
            return self.connection.fetchone()[0]

    def count_update_differences(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE type='update' AND
                                             folder1=? AND folder2=?""",
                                    (folder1, folder2))
            return self.connection.fetchone()[0]

    def select_files_differences(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE (type='new' OR type='update') AND
                                             node_type='f' AND folder1=? AND folder2=?
                                       ORDER BY path ASC""", (folder1, folder2))

            return self.fetch_differences()

    def select_new_file_differences(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE type='new' AND node_type='f' AND
                                             folder1=?  AND folder2=?
                                       ORDER BY path ASC""", (folder1, folder2))

            return self.fetch_differences()

    def select_update_differences(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE type='update' AND folder1=? AND folder2=?
                                       ORDER BY path ASC""", (folder1, folder2))

            return self.fetch_differences()

    def insert_differences(self, diffs):
        with self.connection:
            for i in diffs:
                self.insert_difference(i)

    def get_difference_count(self, folder1, folder2):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE folder1=? AND folder2=?""",
                                    (folder1, folder2))

            return self.connection.fetchone()[0]

    def disable_journal(self):
        self.connection.execute("PRAGMA journal_mode = OFF")

    def enable_journal(self):
        self.connection.execute("PRAGMA journal_mode = DELETE")

    def begin_transaction(self, *args, **kwargs):
        self.connection.begin_transaction(*args, **kwargs)

    def rollback(self):
        self.connection.rollback()

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()
