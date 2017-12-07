#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import Paths
from . import PathMatch
from .FileList import LocalFileList, RemoteFileList, DuplicateList
from .EncPath import EncPath

def try_next(it, default=None):
    try:
        return next(it)
    except StopIteration:
        return default

class FileComparator(object):
    def __init__(self, encsync, name, directory=None):
        self.encsync = encsync

        try:
            self.target = encsync.targets[name]
        except KeyError:
            raise ValueError("Unknown target: %r" % (name,))

        self.directory = directory

        llist = LocalFileList(name, directory)
        rlist = RemoteFileList(name, directory)

        target_local = self.target["dirs"]["local"]
        target_remote = self.target["dirs"]["remote"]

        self.prefix1 = Paths.from_sys(os.path.abspath(os.path.expanduser(target_local)))
        self.prefix1 = Paths.dir_normalize(self.prefix1)
        self.prefix2 = Paths.dir_normalize(Paths.join_properly("/", target_remote))

        self.nodes1 = llist.select_all_nodes()
        self.nodes2 = rlist.select_all_nodes()
        self.duplicates = None

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
        return [("rm", self.type2, self.encpath2, self.target["filename_encoding"])]

    def diff_new(self):
        self.node1 = try_next(self.it1)
        return [("new", self.type1, self.encpath1, self.target["filename_encoding"])]

    def diff_update(self):
        self.node1 = try_next(self.it1)
        self.node2 = try_next(self.it2)
        return [("update", self.type2, self.encpath2, self.target["filename_encoding"])]

    def diff_transition(self):
        self.node1 = try_next(self.it1)
        self.node2 = try_next(self.it2)
        diffs = []
        if self.last_rm is None or not Paths.contains(self.last_rm, self.path2):
            if self.type2 == "d":
                self.last_rm = self.path2
            diffs.append(("rm", self.type2, self.encpath2, self.target["filename_encoding"]))
        diffs.append(("new", self.type1, self.encpath1, self.target["filename_encoding"]))

        return diffs

    def diff_rmdup(self):
        return [("rmdup", self.type2, self.encpath2, self.target["filename_encoding"])]

    def __next__(self):
        while True:
            if self.node1 is None and self.node2 is None:
                break

            if self.node1 is None:
                self.type1 = None
                self.path1 = None
                self.modified1 = None
                self.padded_size1 = None
            else:
                self.type1 = self.node1["type"]
                self.path1 = Paths.cut_prefix(self.node1["path"], self.prefix1) or "/"
                self.modified1 = self.node1["modified"]
                self.padded_size1 = self.node1["padded_size"]

                self.encpath1 = EncPath(self.encsync, self.path1,
                                        self.target["filename_encoding"])
                self.encpath1.local_prefix = self.prefix1
                self.encpath1.remote_prefix = self.prefix2
                self.encpath1.IVs = b""

                assert(self.type1 is not None)

            if self.node2 is None:
                self.type2 = None
                self.path2 = None
                self.modified2 = None
                self.padded_size2 = None
                self.IVs = b""
            else:
                self.type2 = self.node2["type"]
                self.path2 = Paths.cut_prefix(self.node2["path"], self.prefix2) or "/"
                self.modified2 = self.node2["modified"]
                self.padded_size2 = self.node2["padded_size"]
                self.IVs = self.node2["IVs"]

                self.encpath2 = EncPath(self.encsync, self.path2,
                                        self.target["filename_encoding"])
                self.encpath2.local_prefix = self.prefix1
                self.encpath2.remote_prefix = self.prefix2
                self.encpath2.IVs = self.IVs

            if self.path1 is not None and self.target is not None:
                if not PathMatch.match(self.node1["path"], self.target["allowed_paths"]):
                    self.node1 = try_next(self.it1)
                    continue

            if self.is_removed():
                if self.last_rm is None or not Paths.contains(self.last_rm, self.path2):
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

        if self.duplicates is None:
            duplist = DuplicateList(self.directory)
            duplist.create()
            self.duplicates = iter(duplist.find_children(self.prefix2))

        row = try_next(self.duplicates)
        if row is None:
            raise StopIteration

        self.type2 = row[0]
        self.IVs = row[1]
        self.path2 = Paths.cut_prefix(row[2], self.prefix2) or "/"

        self.encpath2 = EncPath(self.encsync, self.path2, self.target["filename_encoding"])
        self.encpath2.local_prefix = self.prefix1
        self.encpath2.remote_prefix = self.prefix2
        self.encpath2.IVs = self.IVs

        return self.diff_rmdup()

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

def compare_lists(encsync, name, directory=None):
    comparator = FileComparator(encsync, name, directory)

    for i in comparator:
        for j in i:
            yield j
