#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import CentDB
from .EncPath import EncPath
from . import Paths

class DiffList(object):
    def __init__(self, encsync, directory=None, *args, **kwargs):
        if directory is None:
            path = "encsync_diffs.db"
        else:
            path = os.path.join(directory, "encsync_diffs.db")

        kwargs.setdefault("isolation_level", None)

        self.conn = CentDB.connect(path, *args, **kwargs)
        self.encsync = encsync

    def __enter__(self):
        self.conn.__enter__()

    def __exit__(self, *args, **kwargs):
        self.conn.__exit__()

    def create(self):
        with self.conn:
            self.conn.execute("""CREATE TABLE IF NOT EXISTS differences
                                 (diff_type TEXT, type TEXT, path TEXT,
                                  local_prefix TEXT, remote_prefix TEXT, IVs TEXT)""")
            self.conn.execute("""CREATE INDEX IF NOT EXISTS differences_path_index
                                 ON differences(path ASC)""")

    def insert_difference(self, diff):
        p = diff[2] # EncPath object
        local_prefix = Paths.dir_normalize(p.local_prefix)
        remote_prefix = Paths.dir_normalize(p.remote_prefix)

        self.conn.execute("""INSERT INTO differences VALUES
                            (?, ?, ?, ?, ?, ?)""",
                          (diff[0], diff[1], p.path, local_prefix, remote_prefix, p.IVs))

    def clear_differences(self, local_prefix, remote_prefix):
        self.conn.execute("""DELETE FROM differences
                             WHERE (local_prefix=? OR local_prefix=?) AND
                                   (remote_prefix=? OR remote_prefix=?)""",
                          (local_prefix, Paths.dir_normalize(local_prefix),
                           remote_prefix, Paths.dir_normalize(remote_prefix)))

    def fetch_differences(self):
        for i in self.conn.genfetch():
            encpath = EncPath(self.encsync, i[2])
            encpath.IVs = i[5]
            encpath.local_prefix = i[3]
            encpath.remote_prefix = i[4]
            yield (i[0], i[1], encpath)

    def select_rm_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT * FROM differences
                                 WHERE diff_type='rm' AND
                                 (local_prefix=? OR local_prefix=?) AND
                                 (remote_prefix=? OR remote_prefix=?) ORDER BY path ASC""",
                              (local_prefix, Paths.dir_normalize(local_prefix),
                               remote_prefix, Paths.dir_normalize(remote_prefix)))
            return self.fetch_differences()

    def select_dirs_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT * FROM differences
                                 WHERE diff_type='new' AND type='d' AND
                                 (local_prefix=? OR local_prefix=?) AND
                                 (remote_prefix=? OR remote_prefix=?) ORDER BY remote_prefix + path ASC""",
                              (local_prefix, Paths.dir_normalize(local_prefix),
                               remote_prefix, Paths.dir_normalize(remote_prefix)))

            return self.fetch_differences()

    def count_dirs_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM differences
                                 WHERE diff_type='new' AND type='d' AND
                                 (local_prefix=? OR local_prefix=?) AND
                                 (remote_prefix=? OR remote_prefix=?)""",
                              (local_prefix, Paths.dir_normalize(local_prefix),
                               remote_prefix, Paths.dir_normalize(remote_prefix)))
            return self.conn.fetchone()[0]

    def count_files_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM differences
                                 WHERE diff_type='new' AND type='f' AND
                                 (local_prefix=? OR local_prefix=?) AND
                                 (remote_prefix=? OR remote_prefix=?)""",
                              (local_prefix, Paths.dir_normalize(local_prefix),
                               remote_prefix, Paths.dir_normalize(remote_prefix)))
            return self.conn.fetchone()[0]

    def count_rm_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM differences
                                 WHERE diff_type='rm' AND
                                 (local_prefix=? OR local_prefix=?) AND
                                 (remote_prefix=? OR remote_prefix=?)""",
                              (local_prefix, Paths.dir_normalize(local_prefix),
                               remote_prefix, Paths.dir_normalize(remote_prefix)))
            return self.conn.fetchone()[0]

    def select_files_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT * FROM differences
                                 WHERE diff_type='new' AND type='f' AND
                                 (local_prefix=? OR local_prefix=?) AND
                                 (remote_prefix=? OR remote_prefix=?) ORDER BY path ASC""",
                              (local_prefix, Paths.dir_normalize(local_prefix),
                               remote_prefix, Paths.dir_normalize(remote_prefix)))

            return self.fetch_differences()

    def insert_differences(self, diffs):
        self.conn.embed(self._insert_differences, diffs)

    def _insert_differences(self, diffs):
        with self.conn:
            for i in diffs:
                self.insert_difference(i)

    def get_difference_count(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM differences
                                 WHERE (local_prefix=? OR local_prefix=?) AND
                                       (remote_prefix=? OR remote_prefix=?)""",
                              (local_prefix, Paths.dir_normalize(local_prefix),
                               remote_prefix, Paths.dir_normalize(remote_prefix)))

            return self.conn.fetchone()[0]

    def begin_transaction(self, *args, **kwargs):
        self.conn.begin_transaction(*args, **kwargs)

    def rollback(self):
        self.conn.rollback()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
