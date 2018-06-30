#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3

from . import cdb, pathm, encryption
from .common import node_tuple_to_dict
from .common import escape_glob, validate_folder_name

__all__ = ["Filelist"]

def prepare_path(path):
    return pathm.dir_denormalize(pathm.join_properly("/", path))

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
                                        modified INTEGER,
                                        padded_size INTEGER,
                                        mode INTEGER,
                                        uid INTEGER,
                                        gid INTEGER,
                                        path TEXT UNIQUE ON CONFLICT REPLACE,
                                        link_path TEXT,
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
        node["path"] = prepare_path(node["path"])

        if node["type"] == "d":
            node["path"] = pathm.dir_normalize(node["path"])

        if node["type"] is None:
            raise ValueError("Node type is None")

        node.setdefault("mode", None)
        node.setdefault("owner", None)
        node.setdefault("group", None)
        node.setdefault("link_path", None)

        self.connection.execute("""INSERT INTO filelist(type, modified, padded_size,
                                                        mode, uid, gid, path,
                                                        link_path, IVs)
                                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (node["type"],
                                 node["modified"] * 1e6,
                                 node["padded_size"],
                                 node["mode"],
                                 node["owner"],
                                 node["group"],
                                 node["path"],
                                 node["link_path"],
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
            self.connection.execute("""SELECT type, modified, padded_size, mode,
                                              uid, gid, path, link_path, IVs
                                       FROM filelist WHERE path=? OR path=? LIMIT 1""",
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
            self.connection.execute("""SELECT type, modified, padded_size, mode,
                                              uid, gid, path, link_path, IVs
                                       FROM filelist WHERE path GLOB ? OR path=? OR path=?
                                       ORDER BY path ASC""",
                                    (pattern, path, path_n))

            return (node_tuple_to_dict(i) for i in self.connection.genfetch())

    def is_empty(self, path="/"):
        """
            Check if the filelist is empty.

            :param path: path of the parent node

            :returns: `bool`
        """

        path = pathm.dir_normalize(prepare_path(path))
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

        parent_dir = pathm.dir_normalize(prepare_path(path))
        parent_dir = escape_glob(path)

        with self.connection:
            self.connection.execute("SELECT COUNT(*) FROM filelist WHERE path GLOB ?",
                                    (parent_dir + "*",))

            return self.connection.fetchone()[0]

    def update_size(self, path, new_size):
        """
            Update node's size.

            :param path: path of the node
            :param new_size: new size
        """

        path = prepare_path(path)

        self.connection.execute("UPDATE filelist SET padded_size=? WHERE path=?",
                                (new_size, path))

    def update_modified(self, path, modified):
        """
            Update node's modified date.

            :param path: path of the node
            :param modified: new modified date
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)

        modified = modified * 1e6

        self.connection.execute("UPDATE filelist SET modified=? WHERE path=? or path=?",
                                (modified, path, path_n))

    def update_mode(self, path, mode):
        """
            Update node's mode.

            :param path: path of the node
            :param mode: `int` or `None`, new file mode
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)

        self.connection.execute("UPDATE filelist SET mode=? WHERE path=? or path=?",
                                (mode, path, path_n))

    def update_owner(self, path, uid):
        """
            Update node's owner.

            :param path: path of the node
            :param uid: `int` or `None`, new owner
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)

        self.connection.execute("UPDATE filelist SET uid=? WHERE path=? or path=?",
                                (uid, path, path_n))

    def update_group(self, path, gid):
        """
            Update node's group.

            :param path: path of the node
            :param gid: `int` or `None`, new group
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)

        self.connection.execute("UPDATE filelist SET gid=? WHERE path=? or path=?",
                                (gid, path, path_n))

    def update_link_path(self, path, link_path):
        """
            Update node's link path.

            :param path: path of the node
            :param link_path: `str`, `bytes` or `None`, new link path
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)

        self.connection.execute("UPDATE filelist SET link_path=? WHERE path=? or path=?",
                                (link_path, path, path_n))

    def find_closest(self, path):
        """
            Find a node that is the closest to `path` (e.g node at `path`, parent node, etc.)

            :param path: node path

            :returns: `dict`
        """

        node = self.find(path)

        while node["path"] is None and path not in ("", "/"):
            path = pathm.dirname(path)
            node = self.find(path)

        return node

    def create_virtual_node(self, path, ivs):
        """
            Create a virtual node if it doesn't exist.

            :param path: path of the node
            :param ivs: node IVs
        """

        self.connection.execute("""INSERT OR FAIL INTO filelist(type, path, IVs, modified)
                                   VALUES(?, ?, ?, ?)""", ("v", path, ivs, 86400))

    def create_virtual_nodes(self, path, prefix):
        """
            Create virtual nodes if they don't exist.

            :param path: path of the node
            :param prefix: prefix, node with empty IVs
        """

        with self.connection:
            closest = self.find_closest(path)
            if pathm.contains(closest["path"], prefix) and not pathm.is_equal(closest["path"], prefix):
                try:
                    self.create_virtual_node(prefix, b"")
                except sqlite3.IntegrityError:
                    pass

                ivs = b""
                cur_path = prefix
            else:
                ivs = closest["IVs"]
                cur_path = closest["path"]

            rel = pathm.relpath(path, cur_path)
            frags = [i for i in rel.split("/") if i]

            for frag in frags:
                cur_path = pathm.join(cur_path, frag)
                ivs += encryption.gen_IV()
                self.create_virtual_node(cur_path, ivs)

        return ivs

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
