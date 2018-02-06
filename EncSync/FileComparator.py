#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import Paths
from . import PathMatch
from .FileList import FileList

__all__ = ["FileComparator", "compare_lists"]

def try_next(it, default=None):
    try:
        return next(it)
    except StopIteration:
        return default

class FileComparator(object):
    def __init__(self, config, folder_name1, folder_name2, directory=None):
        self.config = config

        try:
            self.folder1 = config.folders[folder_name1]
        except KeyError:
            raise ValueError("Unknown folder: %r" % (folder_name1,))

        try:
            self.folder2 = config.folders[folder_name2]
        except KeyError:
            raise ValueError("Unknown folder: %r" % (folder_name2,))

        self.directory = directory

        flist1 = FileList(folder_name1, directory)
        flist2 = FileList(folder_name2, directory)
        flist1.create()
        flist2.create()

        self.prefix1 = self.folder1["path"]
        self.prefix2 = self.folder2["path"]

        self.nodes1 = flist1.select_all_nodes()
        self.nodes2 = flist2.select_all_nodes()

        self.it1 = iter(self.nodes1)
        self.it2 = iter(self.nodes2)

        self.node1 = try_next(self.it1)
        self.node2 = try_next(self.it2)

        self.type1 = None
        self.path1 = None
        self.modified1 = None
        self.padded_size1 = None

        self.type2 = None
        self.path2 = None
        self.modified2 = None
        self.padded_size2 = None

        self.last_rm = None

    def __iter__(self):
        return self

    def diff_rm(self):
        self.node2 = try_next(self.it2)
        if self.type2 == "d":
            self.last_rm = self.path2

        return [{"type": "rm",
                 "node_type": self.type2,
                 "path": self.path2,
                 "folder1": self.folder1["name"],
                 "folder2": self.folder2["name"]}]

    def diff_new(self):
        self.node1 = try_next(self.it1)
        return [{"type": "new",
                 "node_type": self.type1,
                 "path": self.path1,
                 "folder1": self.folder1["name"],
                 "folder2": self.folder2["name"]}]

    def diff_update(self):
        self.node1 = try_next(self.it1)
        self.node2 = try_next(self.it2)

        return [{"type": "update",
                 "node_type": self.type2,
                 "path": self.path2,
                 "folder1": self.folder1["name"],
                 "folder2": self.folder2["name"]}]

    def diff_transition(self):
        self.node1 = try_next(self.it1)
        self.node2 = try_next(self.it2)
        diffs = []
        if self.last_rm is None or not Paths.contains(self.last_rm, self.path2):
            if self.type2 == "d":
                self.last_rm = self.path2

            diffs.append({"type": "rm",
                          "node_type": self.type2,
                          "path": self.path2,
                          "folder1": self.folder1["name"],
                          "folder2": self.folder2["name"]})

        diffs.append({"type": "new",
                      "node_type": self.type1,
                      "path": self.path1,
                      "folder1": self.folder1["name"],
                      "folder2": self.folder2["name"]})

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
                self.path1 = Paths.cut_prefix(self.node1["path"], self.prefix1) or "/"
                self.path1 = Paths.join("/", self.path1)
                self.modified1 = self.node1["modified"]
                self.padded_size1 = self.node1["padded_size"]

                assert(self.type1 is not None)

            if self.node2 is None:
                self.type2 = None
                self.path2 = None
                self.modified2 = None
                self.padded_size2 = None
            else:
                self.type2 = self.node2["type"]
                self.path2 = Paths.cut_prefix(self.node2["path"], self.prefix2) or "/"
                self.path2 = Paths.join("/", self.path2)
                self.modified2 = self.node2["modified"]
                self.padded_size2 = self.node2["padded_size"]

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

def compare_lists(config, folder_name1, folder_name2, directory=None):
    comparator = FileComparator(config, folder_name1, folder_name2, directory)

    for i in comparator:
        for j in i:
            yield j
