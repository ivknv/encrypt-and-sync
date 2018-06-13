#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import cdb, pathm
from .common import escape_glob

__all__ = ["DuplicateList"]

def prepare_path(path):
    return pathm.dir_denormalize(pathm.join_properly("/", path))

class DuplicateList(object):
    def __init__(self, storage_name, directory=None, filename=None, *args, **kwargs):
        if filename is None:
            filename = "%s-duplicates.db" % (storage_name,)

        kwargs = dict(kwargs)
        kwargs.setdefault("isolation_level", None)

        if directory is None:
            path = filename
        else:
            path = os.path.join(directory, filename)

        self.connection = cdb.connect(path, *args, **kwargs)

    def __enter__(self):
        self.connection.__enter__()

    def __exit__(self, *args, **kwargs):
        self.connection.__exit__()

    def time_since_last_commit(self):
        """
            Get the number of seconds since last commit.

            :returns: `float`
        """

        return self.connection.time_since_last_commit()

    def disable_journal(self):
        """Disables journaling."""

        self.connection.disable_journal()

    def enable_journal(self):
        """Enables journaling."""

        self.connection.enable_journal()

    def create(self):
        """Create the duplicate table if it doesn't exist."""

        self.connection.execute("""CREATE TABLE IF NOT EXISTS duplicates
                                   (type TEXT,
                                    IVs TEXT,
                                    path TEXT)""")

    def insert(self, node_type, ivs, path):
        """
            Insert an entry into the database.
            If the node already exists, it will be overwritten.

            :param node_type: "f" or "d", file or directory
            :param ivs: initialization vectors
            :param path: entry path
        """

        path = prepare_path(path)

        if node_type == "d":
            path = pathm.dir_normalize(path)

        self.connection.execute("INSERT INTO duplicates VALUES (?, ?, ?)",
                                (node_type, ivs, path))

    def remove(self, IVs, path):
        """
            Remove the entry from the database.

            :param path: path of the node to be removed
        """

        path = prepare_path(path)

        self.connection.execute("DELETE FROM duplicates WHERE (path=? OR path=?) AND IVs=?",
                          (path, pathm.dir_normalize(path), IVs))

    def remove_recursively(self, path):
        """
            Remove entries recursively from the database.

            :param path: path of the parent node
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)
        pattern = escape_glob(path_n) + "*"

        self.connection.execute("DELETE FROM duplicates WHERE path GLOB ? OR path=? OR path=?",
                                (pattern, path_n, path))

    def clear(self):
        """Delete all entries from the database."""

        self.connection.execute("DELETE FROM duplicates")

    def find(self, ivs, path):
        """
            Find node by its path and initialization vectors.

            :param ivs: `bytes`, initialization vectors
            :param path: path of the node to find

            :returns: `dict`
        """

        path = prepare_path(path)

        with self.connection:
            self.connection.execute("""SELECT * FROM duplicates
                                       WHERE IVs=? AND (path=? OR path=?) LIMIT 1""",
                                    (ivs, path, pathm.dir_normalize(path)))
            return self.connection.fetchone()

    def find_recursively(self, path):
        """
            Find entries by path recursively.

            :param path: path of the parent node

            :returns: iterable of `dict`
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)
        pattern = escape_glob(path_n) + "*"

        with self.connection:
            self.connection.execute("""SELECT * FROM duplicates
                                       WHERE path GLOB ? OR path=? OR path=?
                                       ORDER BY path ASC""",
                                    (pattern, path, path_n))

            return self.connection.genfetch()

    def get_file_count(self, path="/"):
        """
            Get the number of entries in the filelist (contained in `path`)

            :param path: path of the parent node

            :return: `int`
        """

        path = pathm.dir_normalize(prepare_path(path))
        path = escape_glob(path)

        with self.connection:
            self.connection.execute("SELECT COUNT(*) FROM duplicates WHERE path GLOB ?",
                                    (path + "*",))

            return self.connection.fetchone()[0]

    def is_empty(self, path="/"):
        """
            Check if the duplicate list is empty.

            :param path: path of the parent node

            :returns: `bool`
        """

        path = pathm.dir_normalize(prepare_path(path))
        path = escape_glob(path)

        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM
                                       (SELECT * FROM duplicates
                                        WHERE path GLOB ? LIMIT 1)""",
                                    (path + "*",))
            return self.connection.fetchone()[0] == 0

    def begin_transaction(self, *args, **kwargs):
        """Start a transaction."""

        self.connection.begin_transaction(*args, **kwargs)

    def commit(self):
        """Do a commit."""

        self.connection.commit()

    def seamless_commit(self):
        """Do a seamless commit."""

        self.connection.seamless_commit()

    def rollback(self):
        """Do a rollback."""

        self.connection.rollback()

    def close(self):
        """Close the database connection."""

        self.connection.close()
