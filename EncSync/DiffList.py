#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import CDB
from .EncPath import EncPath
from . import Paths

class DiffList(object):
    def __init__(self, encsync, directory=None, *args, **kwargs):
        if directory is None:
            path = "encsync_diffs.db"
        else:
            path = os.path.join(directory, "encsync_diffs.db")

        kwargs.setdefault("isolation_level", None)

        self.connection = CDB.connect(path, *args, **kwargs)
        self.encsync = encsync

    def __enter__(self):
        self.connection.__enter__()

    def __exit__(self, *args, **kwargs):
        self.connection.__exit__()

    def create(self):
        with self.connection:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS differences
                                       (diff_type TEXT, type TEXT, path TEXT,
                                        local_prefix TEXT, remote_prefix TEXT, IVs TEXT,
                                        filename_encoding TEXT)""")
            self.connection.execute("""CREATE INDEX IF NOT EXISTS differences_path_index
                                       ON differences(path ASC)""")

    def insert_difference(self, diff):
        p = diff[2] # EncPath object
        local_prefix = Paths.dir_normalize(p.local_prefix)
        remote_prefix = Paths.dir_normalize(p.remote_prefix)

        self.connection.execute("""INSERT INTO differences VALUES
                                   (?, ?, ?, ?, ?, ?, ?)""",
                                (diff[0], diff[1], p.path, local_prefix, remote_prefix,
                                 p.IVs, diff[3]))

    def clear_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        self.connection.execute("""DELETE FROM differences
                                   WHERE (local_prefix=? OR local_prefix=?) AND
                                         (remote_prefix=? OR remote_prefix=?)""",
                                (local_prefix, Paths.dir_normalize(local_prefix),
                                 remote_prefix, Paths.dir_normalize(remote_prefix)))

    def fetch_differences(self):
        for i in self.connection.genfetch():
            encpath = EncPath(self.encsync, i[2], i[6])
            encpath.IVs = i[5]
            encpath.local_prefix = i[3]
            encpath.remote_prefix = i[4]
            yield (i[0], i[1], encpath)

    def select_rm_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE diff_type='rm' AND
                                      (local_prefix=? OR local_prefix=?) AND
                                      (remote_prefix=? OR remote_prefix=?) ORDER BY path ASC""",
                                    (local_prefix, Paths.dir_normalize(local_prefix),
                                     remote_prefix, Paths.dir_normalize(remote_prefix)))
            return self.fetch_differences()

    def select_rmdup_differences(self, remote_prefix):
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                      WHERE diff_type='rmdup' AND
                                     (remote_prefix=? OR remote_prefix=?) ORDER BY path ASC""",
                                    (remote_prefix, Paths.dir_normalize(remote_prefix)))
            return self.fetch_differences()

    def select_dirs_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE diff_type='new' AND type='d' AND
                                       (local_prefix=? OR local_prefix=?) AND
                                       (remote_prefix=? OR remote_prefix=?) ORDER BY remote_prefix + path ASC""",
                                    (local_prefix, Paths.dir_normalize(local_prefix),
                                     remote_prefix, Paths.dir_normalize(remote_prefix)))

            return self.fetch_differences()

    def count_dirs_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE diff_type='new' AND type='d' AND
                                       (local_prefix=? OR local_prefix=?) AND
                                       (remote_prefix=? OR remote_prefix=?)""",
                                    (local_prefix, Paths.dir_normalize(local_prefix),
                                     remote_prefix, Paths.dir_normalize(remote_prefix)))
            return self.connection.fetchone()[0]

    def count_files_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE diff_type='new' AND type='f' AND
                                       (local_prefix=? OR local_prefix=?) AND
                                       (remote_prefix=? OR remote_prefix=?)""",
                                    (local_prefix, Paths.dir_normalize(local_prefix),
                                     remote_prefix, Paths.dir_normalize(remote_prefix)))
            return self.connection.fetchone()[0]

    def count_rm_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE diff_type='rm' AND
                                       (local_prefix=? OR local_prefix=?) AND
                                       (remote_prefix=? OR remote_prefix=?)""",
                                    (local_prefix, Paths.dir_normalize(local_prefix),
                                     remote_prefix, Paths.dir_normalize(remote_prefix)))
            return self.connection.fetchone()[0]

    def count_rmdup_differences(self, remote_prefix):
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE diff_type='rmdup' AND
                                       (remote_prefix=? OR remote_prefix=?)""",
                                    (remote_prefix, Paths.dir_normalize(remote_prefix)))
            return self.connection.fetchone()[0]

    def count_new_file_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE diff_type='new' AND type='f' AND
                                       (remote_prefix=? OR remote_prefix=?) AND
                                       (local_prefix=? OR local_prefix=?)""",
                                    (remote_prefix, Paths.dir_normalize(remote_prefix),
                                     local_prefix, Paths.dir_normalize(local_prefix)))
            return self.connection.fetchone()[0]

    def count_update_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE diff_type='update' AND
                                       (remote_prefix=? OR remote_prefix=?) AND
                                       (local_prefix=? OR local_prefix=?)""",
                                    (remote_prefix, Paths.dir_normalize(remote_prefix),
                                     local_prefix, Paths.dir_normalize(local_prefix)))
            return self.connection.fetchone()[0]

    def select_files_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE (diff_type='new' OR diff_type='update') AND
                                       type='f' AND (local_prefix=? OR local_prefix=?) AND
                                       (remote_prefix=? OR remote_prefix=?) ORDER BY path ASC""",
                                    (local_prefix, Paths.dir_normalize(local_prefix),
                                     remote_prefix, Paths.dir_normalize(remote_prefix)))

            return self.fetch_differences()

    def select_new_file_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE diff_type='new' AND type='f' AND
                                       (local_prefix=? OR local_prefix=?) AND
                                       (remote_prefix=? OR remote_prefix=?) ORDER BY path ASC""",
                                    (local_prefix, Paths.dir_normalize(local_prefix),
                                     remote_prefix, Paths.dir_normalize(remote_prefix)))

            return self.fetch_differences()

    def select_update_differences(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT * FROM differences
                                       WHERE diff_type='update' AND
                                       (local_prefix=? OR local_prefix=?) AND
                                       (remote_prefix=? OR remote_prefix=?) ORDER BY path ASC""",
                                    (local_prefix, Paths.dir_normalize(local_prefix),
                                     remote_prefix, Paths.dir_normalize(remote_prefix)))

            return self.fetch_differences()

    def insert_differences(self, diffs):
        with self.connection:
            for i in diffs:
                self.insert_difference(i)

    def get_difference_count(self, local_prefix, remote_prefix):
        local_prefix = Paths.from_sys(local_prefix)
        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM differences
                                       WHERE (local_prefix=? OR local_prefix=?) AND
                                             (remote_prefix=? OR remote_prefix=?)""",
                                    (local_prefix, Paths.dir_normalize(local_prefix),
                                     remote_prefix, Paths.dir_normalize(remote_prefix)))

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
