#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import cdb, pathm
from .common import node_tuple_to_dict, format_timestamp
from .common import escape_glob, validate_folder_name

__all__ = ["Filelist"]

def prepare_path(path):
    return pathm.join_properly("/", path)

class Filelist(object):
    def __init__(self, folder_name, directory=None, *args, **kwargs):
        if not validate_folder_name(folder_name):
            raise ValueError("Invalid folder name: %r" % (folder_name,))

        kwargs = dict(kwargs)
        kwargs.setdefault("isolation_level", None)

        filename = "%s-filelist.db" % (folder_name,)

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

    def create(self):
        """Create the filelist table if it doesn't exist."""

        with self.connection:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS filelist
                                       (type TEXT,
                                        modified DATETIME,
                                        padded_size INTEGER,
                                        path TEXT UNIQUE ON CONFLICT REPLACE,
                                        IVs TEXT)""")
            self.connection.execute("""CREATE INDEX IF NOT EXISTS path_index
                                       ON filelist(path ASC)""")

    def disable_journal(self):
        """Disables journaling."""

        self.connection.disable_journal()

    def enable_journal(self):
        """Enables journaling."""

        self.connection.enable_journal()

    def insert(self, node):
        """
            Insert the node into the database.
            If the node already exists, it will be overwritten.

            :param node: `dict`, node to be inserted
        """

        node = dict(node)
        if node["type"] == "d":
            node["path"] = pathm.dir_normalize(node["path"])

        if node["type"] is None:
            raise ValueError("Node type is None")

        self.connection.execute("""INSERT INTO filelist VALUES
                                   (?, ?, ?, ?, ?)""",
                                (node["type"],
                                 format_timestamp(node["modified"]),
                                 node["padded_size"],
                                 prepare_path(node["path"]),
                                 node["IVs"]))

    def remove(self, path):
        """
            Remove the node from the database.

            :param path: path of the node to be removed
        """

        path = prepare_path(path)

        self.connection.execute("DELETE FROM filelist WHERE path=? OR path=?",
                                (path, pathm.dir_normalize(path)))

    def remove_recursively(self, path):
        """
            Remove nodes recursively from the database.

            :param path: path of the parent node
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)
        pattern = escape_glob(path_n) + "*"

        self.connection.execute("DELETE FROM filelist WHERE path GLOB ? OR path=? OR path=?",
                                (pattern, path_n, path))

    def clear(self):
        """Delete all nodes from the database."""

        self.connection.execute("DELETE FROM filelist")

    def find(self, path):
        """
            Find node by its path.

            :param path: path of the node to find

            :returns: `dict`
        """

        path = prepare_path(path)

        with self.connection:
            self.connection.execute("""SELECT * FROM filelist
                                       WHERE path=? OR path=? LIMIT 1""",
                                    (path, pathm.dir_normalize(path)))
            return node_tuple_to_dict(self.connection.fetchone())

    def find_recursively(self, path):
        """
            Find nodes by path recursively.

            :param path: path of the parent node

            :returns: iterable of `dict`
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)
        pattern = escape_glob(path_n) + "*"

        with self.connection:
            self.connection.execute("""SELECT * FROM filelist
                                       WHERE path GLOB ? OR path=? OR path=?
                                       ORDER BY path ASC""",
                                    (pattern, path, path_n))

            return (node_tuple_to_dict(i) for i in self.connection.genfetch())

    def is_empty(self, path="/"):
        """
            Check if the filelist is empty.

            :param path: path of the parent node

            :returns: `bool`
        """

        path = prepare_path(pathm.dir_normalize(path))
        path = escape_glob(path)

        with self.connection:
            self.connection.execute("""SELECT COUNT(*) FROM
                                       (SELECT * FROM filelist
                                        WHERE path GLOB ? LIMIT 1)""",
                                    (path + "*",))

            return self.connection.fetchone()[0] == 0

    def get_file_count(self, path="/"):
        """
            Get the number of nodes in the filelist (contained in `path`)

            :param path: path of the parent node

            :return: `int`
        """

        parent_dir = prepare_path(pathm.dir_normalize(path))
        parent_dir = escape_glob(path)

        with self.connection:
            self.connection.execute("SELECT COUNT(*) FROM filelist WHERE path GLOB ?",
                                    (parent_dir + "*",))

            return self.connection.fetchone()[0]

    def update_size(self, path, new_size):
        """
            Update node size.

            :param path: path of the node
            :param new_size: new size
        """

        self.connection.execute("UPDATE filelist SET padded_size=? WHERE path=?",
                                (new_size, path))

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
