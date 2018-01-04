#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from .. import CDB

__all__ = ["BaseFileList"]

class BaseFileList(object):
    def __init__(self, filename, directory=None, *args, **kwargs):
        kwargs = dict(kwargs)

        kwargs.setdefault("isolation_level", None)

        if directory is None:
            path = filename
        else:
            path = os.path.join(directory, filename)

        self.connection = CDB.connect(path, *args, **kwargs)

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

        raise NotImplementedError

    def disable_journal(self):
        """Disables journaling."""

        self.connection.execute("PRAGMA journal_mode = OFF")

    def enable_journal(self):
        """Enables journaling."""

        self.connection.execute("PRAGMA journal_mode = DELETE")

    def insert_node(self, node):
        """
            Insert the node into the database.
            If the node already exists, it will be overwritten.

            :param node: `dict`, node to be inserted
        """

        raise NotImplementedError

    def remove_node(self, path):
        """
            Remove node from the database.

            :param path: path of the node to be removed
        """

        raise NotImplementedError

    def remove_node_children(self, path):
        """
            Remove node's children from the database.

            :param path: path of the parent node
        """

        raise NotImplementedError

    def clear(self):
        """Delete all nodes from the database."""

        raise NotImplementedError

    def find_node(self, path):
        """
            Find node by its path.

            :param path: path of the node to find

            :returns: `dict`
        """

        raise NotImplementedError

    def find_node_children(self, path):
        """
            Find node children by path.

            :param path: path of the parent node

            :returns: iterable of `dict`
        """

        raise NotImplementedError

    def select_all_nodes(self):
        """
            List all the nodes in the database.

            :returns: iterable of `dict`
        """

        raise NotImplementedError

    def insert_nodes(self, nodes):
        """
            Insert multiple nodes into the database.

            :param nodes: iterable of `dict`
        """

        for i in nodes:
            self.insert_node(i)

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
