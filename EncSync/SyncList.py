#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
from datetime import datetime
import sqlite3

from .YandexDiskApi import parse_date
from . import paths
from .EncPath import EncPath
from . import CentDB
from .Encryption import MIN_ENC_SIZE

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime(DATE_FORMAT)

def parse_timestamp(s):
    return datetime.strptime(s, DATE_FORMAT).timestamp()

def pad_size(size):
    if size % 16 == 0:
        return size

    return size + 16 - (size % 16)

def node_tuple_to_dict(t):
    if t is not None:
        return {"type": t[0],
                "modified": parse_timestamp(t[1]),
                "padded_size": t[2],
                "path": t[3],
                "IVs": t[4] if len(t) >= 5 else b""}
    else:
        return {"type": None,
                "modified": None,
                "padded_size": None,
                "path": None,
                "IVs": None}

def normalize_node(node, local=True):
    if local:
        node["path"] = paths.from_sys(node["path"])
    if node["type"] == "d":
        node["path"] = paths.dir_normalize(node["path"])

class DiffList(object):
    def __init__(self, encsync, path=None, *args, **kwargs):
        if path is None:
            path = "encsync_diffs.db"

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
        self.conn.execute("""INSERT INTO differences VALUES
                            (?, ?, ?, ?, ?, ?)""",
                          (diff[0], diff[1], p.path, p.local_prefix,
                           p.remote_prefix, p.IVs))

    def clear_differences(self, local_prefix, remote_prefix):
        self.conn.execute("""DELETE FROM differences
                             WHERE local_prefix=? AND remote_prefix=?""",
                          (local_prefix, remote_prefix))

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
                                 local_prefix=? AND remote_prefix=? ORDER BY path ASC""",
                              (local_prefix, remote_prefix))
            return self.fetch_differences()

    def select_dirs_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT * FROM differences
                                 WHERE diff_type='new' AND type='d' AND
                                 local_prefix=? AND remote_prefix=? ORDER BY path ASC""",
                              (local_prefix, remote_prefix))

            return self.fetch_differences()

    def count_dirs_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM differences
                                 WHERE diff_type='new' AND type='d' AND
                                 local_prefix=? AND remote_prefix=?""",
                              (local_prefix, remote_prefix))
            return self.conn.fetchone()[0]

    def count_files_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM differences
                                 WHERE diff_type='new' AND type='f' AND
                                 local_prefix=? AND remote_prefix=?""",
                              (local_prefix, remote_prefix))
            return self.conn.fetchone()[0]

    def count_rm_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM differences
                                 WHERE diff_type='rm' AND
                                 local_prefix=? AND remote_prefix=?""",
                              (local_prefix, remote_prefix))
            return self.conn.fetchone()[0]

    def select_files_differences(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT * FROM differences
                                 WHERE diff_type='new' AND type='f' AND
                                 local_prefix=? AND remote_prefix=? ORDER BY path ASC""",
                              (local_prefix, remote_prefix))

            return self.fetch_differences()

    def insert_differences(self, diffs):
        with self.conn:
            for i in diffs:
                self.insert_difference(i)

    def get_difference_count(self, local_prefix, remote_prefix):
        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM differences
                                 WHERE local_prefix=? AND remote_prefix=?""",
                              (local_prefix, remote_prefix))

            return self.conn.fetchone()[0]

    def begin_transaction(self, *args, **kwargs):
        self.conn.begin_transaction(*args, **kwargs)

    def rollback(self):
        self.conn.rollback()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

class SyncList(object):
    def __init__(self, path=None, *args, **kwargs):
        if path is None:
            path = "encsync.db"
        kwargs.setdefault("isolation_level", None)
        self.conn = CentDB.connect(path, *args, **kwargs)

    def __enter__(self):
        self.conn.__enter__()

    def __exit__(self, *args, **kwargs):
        self.conn.__exit__()

    def create(self):
        with self.conn:
            self.conn.execute("""CREATE TABLE IF NOT EXISTS local_filelist
                                (type TEXT,
                                 modified DATETIME,
                                 padded_size INTEGER,
                                 path TEXT UNIQUE ON CONFLICT REPLACE)""")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS remote_filelist
                                (type TEXT,
                                 modified DATETIME,
                                 padded_size INTEGER,
                                 path TEXT UNIQUE ON CONFLICT REPLACE,
                                 IVs TEXT)""")
            self.conn.execute("""CREATE INDEX IF NOT EXISTS local_path_index
                                ON local_filelist(path ASC)""")
            self.conn.execute("""CREATE INDEX IF NOT EXISTS remote_path_index
                                ON remote_filelist(path ASC)""")

    def insert_local_node(self, node):
        node = dict(node)
        normalize_node(node, True)

        self.conn.execute("""INSERT INTO local_filelist VALUES
                             (?, ?, ?, ?)""",
                          (node["type"],
                           format_timestamp(node["modified"]),
                           node["padded_size"],
                           node["path"]))

    def update_local_size(self, path, new_size):
        self.conn.execute("""UPDATE local_filelist
                             SET padded_size=? WHERE path=?""",
                          (new_size, path))

    def insert_remote_node(self, node):
        node = dict(node)
        normalize_node(node, False)

        self.conn.execute("""INSERT INTO remote_filelist VALUES
                            (?, ?, ?, ?, ?)""",
                          (node["type"],
                           format_timestamp(node["modified"]),
                           node["padded_size"],
                           node["path"],
                           node["IVs"]))

    def remove_remote_node(self, path):
        self.conn.execute("""DELETE FROM remote_filelist
                             WHERE path=? OR path=?""",
                          (path, paths.dir_normalize(path)))

    def remove_remote_node_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        self.conn.execute("DELETE FROM remote_filelist WHERE path LIKE ? ESCAPE '\\'",
                          (path + "%",))

    def remove_local_node(self, path):
        self.conn.execute("""DELETE FROM local_filelist
                             WHERE path=? OR path=?""",
                          (path, paths.dir_normalize(path)))

    def remove_local_node_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        self.conn.execute("DELETE FROM local_filelist WHERE path LIKE ? ESCAPE '\\'",
                          (path + "%",))

    def clear_local(self):
        self.conn.execute("""DELETE FROM local_filelist""")

    def clear_remote(self):
        self.conn.execute("""DELETE FROM remote_filelist""")

    def find_local_node(self, path):
        with self.conn:
            self.conn.execute("""SELECT * FROM local_filelist
                                 WHERE path=? OR path=? LIMIT 1""",
                              (path, paths.dir_normalize(path)))
            return node_tuple_to_dict(self.conn.fetchone())

    def find_remote_node(self, path):
        with self.conn:
            self.conn.execute("""SELECT * FROM remote_filelist
                                 WHERE path=? OR path=? LIMIT 1""",
                              (path, paths.dir_normalize(path)))
            return node_tuple_to_dict(self.conn.fetchone())

    def find_local_node_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT * FROM local_filelist
                                WHERE path LIKE ? ESCAPE '\\' ORDER BY path ASC""",
                              (path + "%",))

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def find_remote_node_children(self, path):
        path = paths.dir_normalize(path)

        path = path.replace("%", "\\%")
        path = path.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT * FROM remote_filelist
                                WHERE path LIKE ? ESCAPE '\\' ORDER BY path ASC""",
                              (path + "%",))

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def select_all_local_nodes(self):
        with self.conn:
            self.conn.execute("""SELECT * FROM local_filelist ORDER BY path ASC""")

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def select_all_remote_nodes(self):
        with self.conn:
            self.conn.execute("""SELECT * FROM remote_filelist ORDER BY path ASC""")

            return (node_tuple_to_dict(i) for i in self.conn.genfetch())

    def insert_local_nodes(self, nodes):
        with self.conn:
            for i in nodes:
                self.insert_local_node(i)

    def insert_remote_nodes(self, nodes):
        with self.conn:
            for i in nodes:
                self.insert_remote_node(i)

    def is_remote_list_empty(self, parent_dir="/"):
        parent_dir = paths.dir_normalize(parent_dir)

        parent_dir = parent_dir.replace("%", "\\%")
        parent_dir = parent_dir.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM remote_filelist
                                 WHERE path LIKE ? ESCAPE '\\' LIMIT 1""",
                              (parent_dir + "%",))

            return self.conn.fetchone()[0] == 0

    def get_remote_file_count(self, parent_dir="/"):
        parent_dir = paths.dir_normalize(parent_dir)

        parent_dir = parent_dir.replace("%", "\\%")
        parent_dir = parent_dir.replace("_", "\\_")

        with self.conn:
            self.conn.execute("""SELECT COUNT(*) FROM remote_filelist
                                 WHERE path LIKE ? ESCAPE '\\'""",
                              (parent_dir + "%",))

            return self.conn.fetchone()[0]

    def begin_transaction(self, *args, **kwargs):
        self.conn.begin_transaction(*args, **kwargs)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

def try_next(it, default=None):
    try:
        return next(it)
    except StopIteration:
        return default

def scan_files(path):
    path = os.path.abspath(os.path.expanduser(path))

    flist = [os.path.join(path, i) for i in os.listdir(path)]
    flist.sort(reverse=True) # reverse=True to counteract the stack ordering

    while len(flist):
        node = {}
        p = flist.pop()

        node["path"] = p

        if os.path.isfile(p):
            node["type"] = "f"
            node["padded_size"] = pad_size(os.path.getsize(p))
        elif os.path.isdir(p):
            node["type"] = "d"
            node["padded_size"] = 0
        else:
            continue

        node["modified"] = datetime.utcfromtimestamp(os.path.getmtime(p)).timestamp()
        node["IVs"] = b""

        normalize_node(node)

        yield node

        if node["type"] == "d":
            new_flist = [os.path.join(p, i) for i in os.listdir(p)]
            new_flist.sort(reverse=True) # reverse=True to counteract the stack ordering
            flist.extend(new_flist)

def scan_files_ynd(path, encsync):
    dec_path = path

    yn = encsync.ynd

    flist = []

    data = None

    for j in range(10):
        dirs = []
        try:
            for i in yn.ls(path):
                data = i["data"]
                data["name"] = paths.join(path, data["name"])
                data["dec_name"], data["IVs"] = encsync.decrypt_path(data["name"], path)
                dirs.append(data)
            flist.extend(dirs)
            del dirs
            break
        except Exception as e:
            if j == 9:
                raise e

    flist.sort(key=lambda x: x["dec_name"], reverse=True)

    while len(flist):
        node = {}
        i = flist.pop()
        p = i["name"]
        dec_p = i["dec_name"]

        node["path"] = dec_p
        node["IVs"] = i["IVs"]

        if i["type"] == "file":
            node["type"] = "f"
            node["padded_size"] = i["size"] - MIN_ENC_SIZE
        elif i["type"] == "dir":
            node["type"] = "d"
            node["padded_size"] = 0
        else:
            continue

        date = i["modified"]

        node["modified"] = time.mktime(parse_date(date))

        normalize_node(node)

        yield node

        if node["type"] == "d":
            for j in range(10):
                new_flist = []
                try:
                    for i in yn.ls(p):
                        data = i["data"]
                        data["name"] = paths.join(p, data["name"])
                        data["dec_name"], data["IVs"] = encsync.decrypt_path(data["name"], path)
                        new_flist.append(data)

                    new_flist.sort(key=lambda x: x["dec_name"], reverse=True)
                    flist.extend(new_flist)
                    del new_flist
                    break
                except Exception as e:
                    if j == 9:
                        raise e

class Comparator(object):
    def __init__(self, encsync, prefix1, prefix2):
        self.encsync = encsync
        self.prefix1 = paths.from_sys(prefix1)
        self.prefix2 = prefix2

        synclist1, synclist2 = SyncList(), SyncList()

        self.nodes1 = synclist1.find_local_node_children(prefix1)
        self.nodes2 = synclist2.find_remote_node_children(prefix2)

        self.it1 = iter(self.nodes1)
        self.it2 = iter(self.nodes2)

        self.node1 = try_next(self.it1)
        self.node2 = try_next(self.it2)

        self.type1 = None
        self.path1 = None
        self.modified1 = None
        self.padded_size1 = None
        self.encpath1 = None

        self.type2 = None
        self.path2 = None
        self.modified2 = None
        self.padded_size2 = None
        self.IVs = None
        self.encpath2 = None

        self.last_rm = None

    def __iter__(self):
        return self

    def diff_rm(self):
        self.node2 = try_next(self.it2)
        if self.type2 == "d":
            self.last_rm = self.path2
        return [("path no longer exists", "rm", self.type2, self.encpath2)[1:]]

    def diff_new(self):
        self.node1 = try_next(self.it1)
        return [("path is new", "new", self.type1, self.encpath1)[1:]]

    def diff_update(self):
        self.node1 = try_next(self.it1)
        self.node2 = try_next(self.it2)
        return [("path is newer", "new", self.type2, self.encpath2)[1:]]

    def diff_transition(self):
        self.node1 = try_next(self.it1)
        self.node2 = try_next(self.it2)
        diffs = []
        if self.last_rm is None or not paths.contains(self.last_rm, self.path2):
            if self.type2 == "d":
                self.last_rm = self.path2
            diffs.append(("file <==> dir transition", "rm", self.type2, self.encpath2)[1:])
        diffs.append(("file <==> dir transition", "new", self.type1, self.encpath1)[1:])

        return diffs

    def __next__(self):
        while True:
            if self.node1 is None and self.node2 is None:
                raise StopIteration

            if self.node1 is None:
                self.type1 = None
                self.path1 = None
                self.modified1 = None
                self.padded_size1 = None
            else:
                self.type1 = self.node1["type"]
                self.path1 = paths.cut_prefix(self.node1["path"], self.prefix1)
                self.modified1 = self.node1["modified"]
                self.padded_size1 = self.node1["padded_size"]

                self.encpath1 = EncPath(self.encsync, self.path1)
                self.encpath1.local_prefix = self.prefix1
                self.encpath1.remote_prefix = self.prefix2
                self.encpath1.IVs = b""

            if self.node2 is None:
                self.type2 = None
                self.path2 = None
                self.modified2 = None
                self.padded_size2 = None
                self.IVs = b""
            else:
                self.type2 = self.node2["type"]
                self.path2 = paths.cut_prefix(self.node2["path"], self.prefix2)
                self.modified2 = self.node2["modified"]
                self.padded_size2 = self.node2["padded_size"]
                self.IVs = self.node2["IVs"]

                self.encpath2 = EncPath(self.encsync, self.path2)
                self.encpath2.local_prefix = self.prefix1
                self.encpath2.remote_prefix = self.prefix2
                self.encpath2.IVs = self.IVs

            if self.is_removed():
                if self.last_rm is None or not paths.contains(self.last_rm, self.path2):
                    return self.diff_rm()
                else:
                    self.node2 = try_next(self.it2)
            elif self.is_new():
                return self.diff_new()
            elif self.is_transitioned():
                return self.diff_transition()
            elif self.is_newer():
                return self.diff_update()
            else:
                self.node1 = try_next(self.it1)
                self.node2 = try_next(self.it2)

    def is_newer(self):
        condition = self.node1 is not None and self.node2 is not None
        condition = condition and self.type1 == "f"
        condition = condition and (self.modified1 > self.modified2 or
                                   self.padded_size1 != self.padded_size2)

        return condition

    def is_new(self):
        condition = self.node1 is not None
        condition = condition and (self.node2 is None or self.path1 < self.path2)

        return condition

    def is_removed(self):
        return self.node2 and (self.node1 is None or
                               (self.node1 and self.path1 > self.path2))

    def is_transitioned(self):
        return self.node1 and self.node2 and self.type1 != self.type2

def compare_lists(encsync, prefix1, prefix2):
    comparator = Comparator(encsync, prefix1, prefix2)

    for i in comparator:
        for j in i:
            yield j
