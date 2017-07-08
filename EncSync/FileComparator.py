#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
    def __init__(self, encsync, prefix1, prefix2, directory=None):
        self.encsync = encsync
        self.prefix1 = Paths.from_sys(prefix1)
        self.prefix2 = Paths.dir_normalize(prefix2)
        self.directory = directory

        self.target = None

        for i in encsync.targets:
            if Paths.dir_normalize(i["remote"]) == self.prefix2:
                self.target = i

        llist, rlist = LocalFileList(directory), RemoteFileList(directory)

        self.nodes1 = llist.find_node_children(self.prefix1)
        self.nodes2 = rlist.find_node_children(self.prefix2)
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
        if self.last_rm is None or not Paths.contains(self.last_rm, self.path2):
            if self.type2 == "d":
                self.last_rm = self.path2
            diffs.append(("file <==> dir transition", "rm", self.type2, self.encpath2)[1:])
        diffs.append(("file <==> dir transition", "new", self.type1, self.encpath1)[1:])

        return diffs

    def diff_rmdup(self):
        return [("duplicate", "rmdup", self.type2, self.encpath2)[1:]]

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
                self.path2 = Paths.cut_prefix(self.node2["path"], self.prefix2) or "/"
                self.modified2 = self.node2["modified"]
                self.padded_size2 = self.node2["padded_size"]
                self.IVs = self.node2["IVs"]

                self.encpath2 = EncPath(self.encsync, self.path2)
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

        self.encpath2 = EncPath(self.encsync, self.path2)
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

def compare_lists(encsync, prefix1, prefix2, directory=None):
    comparator = FileComparator(encsync, prefix1, prefix2, directory)

    for i in comparator:
        for j in i:
            yield j
