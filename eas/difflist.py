# -*- coding: utf-8 -*-

import os

from . import cdb

__all__ = ["DiffList"]

class DiffList(object):
    def __init__(self, directory=None, *args, **kwargs):
        if directory is None:
            path = "eas_diffs.db"
        else:
            path = os.path.join(directory, "eas_diffs.db")

        kwargs.setdefault("isolation_level", None)

        self.connection = cdb.connect(path, *args, **kwargs)

    def __enter__(self):
        self.connection.__enter__()

    def __exit__(self, *args, **kwargs):
        self.connection.__exit__()

    def create(self):
        with self.connection:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS differences
                                       (type TEXT, node_type TEXT,
                                        path TEXT, src_path TEXT, dst_path TEXT)""")
            self.connection.execute("""CREATE INDEX IF NOT EXISTS differences_path_index
                                       ON differences(path ASC)""")

    def insert_difference(self, diff):
        diff_type = diff["type"]
        node_type = diff["node_type"]
        path = diff["path"]
        src_path = diff["src_path"]
        dst_path = diff["dst_path"]

        self.connection.execute("INSERT INTO differences VALUES (?, ?, ?, ?, ?)",
                                (diff_type, node_type, path, src_path, dst_path))

    def clear_differences(self, src_path, dst_path):
        self.connection.execute("""DELETE FROM differences WHERE
                                   src_path=? AND dst_path=?""", (src_path, dst_path))

    def fetch_differences(self):
        for i in self.connection.genfetch():
            yield {"type": i[0],
                   "node_type": i[1],
                   "path": i[2],
                   "src_path": i[3],
                   "dst_path": i[4]}

    def select_rm_differences(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE type='rm' AND src_path=? AND dst_path=?
                                       ORDER BY path ASC""", (src_path, dst_path))
            return self.fetch_differences()

    def select_dirs_differences(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE type='new' AND node_type='d' AND
                                             src_path=? AND dst_path=?
                                       ORDER BY path ASC""", (src_path, dst_path))

            return self.fetch_differences()

    def count_dirs_differences(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE type='new' AND node_type='d' AND
                                             src_path=?  AND dst_path=?""",
                                    (src_path, dst_path))
            return self.connection.fetchone()[0]

    def count_files_differences(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE (type='new' OR type='update') AND
                                             node_type='f' AND src_path=?  AND dst_path=?""",
                                    (src_path, dst_path))
            return self.connection.fetchone()[0]

    def count_rm_differences(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE type='rm' AND src_path=? AND dst_path=?""",
                                    (src_path, dst_path))
            return self.connection.fetchone()[0]

    def count_new_file_differences(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE type='new' AND node_type='f' AND
                                             src_path=? AND dst_path=?""",
                                    (src_path, dst_path))
            return self.connection.fetchone()[0]

    def count_update_differences(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE type='update' AND
                                             src_path=? AND dst_path=?""",
                                    (src_path, dst_path))
            return self.connection.fetchone()[0]

    def select_files_differences(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE (type='new' OR type='update') AND
                                             node_type='f' AND src_path=? AND dst_path=?
                                       ORDER BY path ASC""", (src_path, dst_path))

            return self.fetch_differences()

    def select_new_file_differences(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE type='new' AND node_type='f' AND
                                             src_path=?  AND dst_path=?
                                       ORDER BY path ASC""", (src_path, dst_path))

            return self.fetch_differences()

    def select_update_differences(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE type='update' AND src_path=? AND dst_path=?
                                       ORDER BY path ASC""", (src_path, dst_path))

            return self.fetch_differences()

    def insert_differences(self, diffs):
        with self.connection:
            for i in diffs:
                self.insert_difference(i)

    def get_difference_count(self, src_path, dst_path):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE src_path=? AND dst_path=?""",
                                    (src_path, dst_path))

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
