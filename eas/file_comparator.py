# -*- coding: utf-8 -*-

from . import pathm
from .filelist import Filelist
from .common import recognize_path

__all__ = ["FileComparator", "compare_lists"]

def try_next(it, default=None):
    try:
        return next(it)
    except StopIteration:
        return default

class FileComparator(object):
    def __init__(self, config, src_path, dst_path, directory=None,
                 checks=("rm", "new", "update", "modified", "chmod")):
        self.config = config

        src_path, src_path_type = recognize_path(src_path)
        dst_path, dst_path_type = recognize_path(dst_path)

        src_path = pathm.join_properly("/", src_path)
        dst_path = pathm.join_properly("/", dst_path)

        self.src_path = src_path
        self.dst_path = dst_path

        self.src_path_with_proto = src_path_type + "://" + src_path
        self.dst_path_with_proto = dst_path_type + "://" + dst_path

        folder1 = config.identify_folder(src_path_type, src_path)
        folder2 = config.identify_folder(dst_path_type, dst_path)

        if folder1 is None:
            raise KeyError("%r does not belong to any known folders" % (self.src_path,))

        if folder2 is None:
            raise KeyError("%r does not belong to any known folders" % (self.dst_path,))

        self.directory = directory

        flist1 = Filelist(folder1["name"], directory)
        flist2 = Filelist(folder2["name"], directory)
        flist1.create()
        flist2.create()

        self.prefix1 = folder1["path"]
        self.prefix2 = folder2["path"]

        self.nodes1 = flist1.find_recursively(src_path)
        self.nodes2 = flist2.find_recursively(dst_path)

        self.it1 = iter(self.nodes1)
        self.it2 = iter(self.nodes2)

        self.node1 = try_next(self.it1)
        self.node2 = try_next(self.it2)

        self.type1 = None
        self.path1 = None
        self.modified1 = None
        self.padded_size1 = None
        self.mode1 = None
        self.link_path1 = None

        self.type2 = None
        self.path2 = None
        self.modified2 = None
        self.padded_size2 = None
        self.mode2 = None
        self.link_path2 = None

        self.last_rm = None

        self.checks = checks

    def __iter__(self):
        return self

    def diff_rm(self):
        if self.type2 == "d":
            self.last_rm = self.path2

        yield {"type": "rm",
               "node_type": self.type2,
               "path": self.path2,
               "link_path": None,
               "src_path": self.src_path_with_proto,
               "dst_path": self.dst_path_with_proto}

    def diff_new(self):
        yield {"type": "new",
               "node_type": self.type1,
               "path": self.path1,
               "link_path": self.link_path1,
               "src_path": self.src_path_with_proto,
               "dst_path": self.dst_path_with_proto}

    def diff_update(self):
        yield {"type": "update",
               "node_type": self.type2,
               "path": self.path2,
               "link_path": None,
               "src_path": self.src_path_with_proto,
               "dst_path": self.dst_path_with_proto}

    def diff_transition(self):
        if self.last_rm is None or not pathm.contains(self.last_rm, self.path2):
            if self.type2 == "d":
                self.last_rm = self.path2

            yield {"type": "rm",
                   "node_type": self.type2,
                   "path": self.path2,
                   "link_path": None,
                   "src_path": self.src_path_with_proto,
                   "dst_path": self.dst_path_with_proto}

        yield {"type": "new",
               "node_type": self.type1,
               "path": self.path1,
               "link_path": self.link_path1,
               "src_path": self.src_path_with_proto,
               "dst_path": self.dst_path_with_proto}

    def diff_modified(self):
        yield {"type": "modified",
               "node_type": self.type2,
               "path": self.path2,
               "link_path": None,
               "src_path": self.src_path_with_proto,
               "dst_path": self.dst_path_with_proto}

    def diff_chmod(self):
        yield {"type": "chmod",
               "node_type": self.type2,
               "path": self.path2,
               "link_path": None,
               "src_path": self.src_path_with_proto,
               "dst_path": self.dst_path_with_proto}

    def __next__(self):
        while True:
            if self.node1 is None and self.node2 is None:
                raise StopIteration

            if self.node1 is None:
                self.type1 = None
                self.path1 = None
                self.modified1 = None
                self.padded_size1 = None
                self.mode1 = None
                self.link_path1 = None
            else:
                self.type1 = self.node1["type"]
                self.path1 = pathm.cut_prefix(self.node1["path"], self.src_path) or "/"
                self.path1 = pathm.join("/", self.path1)
                self.modified1 = self.node1["modified"]
                self.padded_size1 = self.node1["padded_size"]
                self.mode1 = self.node1["mode"]
                self.link_path1 = self.node1["link_path"]

                assert(self.type1 is not None)

            if self.node2 is None:
                self.type2 = None
                self.path2 = None
                self.modified2 = None
                self.padded_size2 = None
                self.mode2 = None
                self.link_path2 = None
            else:
                self.type2 = self.node2["type"]
                self.path2 = pathm.cut_prefix(self.node2["path"], self.dst_path) or "/"
                self.path2 = pathm.join("/", self.path2)
                self.modified2 = self.node2["modified"]
                self.padded_size2 = self.node2["padded_size"]
                self.mode2 = self.node2["mode"]
                self.link_path2 = self.node2["link_path"]

                assert(self.type2 is not None)

            diffs = []
                
            if self.is_removed():
                self.node2 = try_next(self.it2)

                if self.last_rm is None or not pathm.contains(self.last_rm, self.path2):
                    diffs.extend(self.diff_rm())
            elif self.is_new():
                self.node1 = try_next(self.it1)

                diffs.extend(self.diff_new())
            elif self.is_transitioned():
                self.node1 = try_next(self.it1)
                self.node2 = try_next(self.it2)

                diffs.extend(self.diff_transition())
            else:
                if self.is_newer():
                    diffs.extend(self.diff_update())

                if self.is_modified_different():
                    diffs.extend(self.diff_modified())

                if self.is_mode_different():
                    diffs.extend(self.diff_chmod())

                self.node1 = try_next(self.it1)
                self.node2 = try_next(self.it2)

            if diffs:
                return diffs

    def is_newer(self):
        if "new" not in self.checks:
            return False

        if self.link_path1 is not None or self.link_path2 is not None:
            return False

        return (self.node1 and self.node2) and (self.type1 == "f" and
                                                (self.modified1 > self.modified2 or
                                                 self.padded_size1 != self.padded_size2))

    def is_new(self):
        if "update" not in self.checks:
            return False

        return self.node1 and (not self.node2 or self.path1 < self.path2)

    def is_removed(self):
        if "rm" not in self.checks:
            return False

        return self.node2 and (not self.node1 or
                               (self.node1 and self.path1 > self.path2))

    def is_transitioned(self):
        if "new" not in self.checks or "rm" not in self.checks:
            return False

        return self.node1 and self.node2 and (self.type1 != self.type2 and
                                              self.link_path1 is None and
                                              self.link_path2 is None or
                                              self.link_path1 != self.link_path2)

    def is_modified_different(self):
        if "modified" not in self.checks:
            return False

        return self.node1 and self.node2 and (self.path1 == self.path2 and
                                              self.modified1 != self.modified2)

    def is_mode_different(self):
        if "chmod" not in self.checks:
            return False

        return self.node1 and self.node2 and (self.path1 == self.path2 and
                                              self.mode1 != self.mode2)

def compare_lists(config, src_path, dst_path, directory=None,
                  checks=("rm", "new", "update", "modified", "chmod")):
    comparator = FileComparator(config, src_path, dst_path, directory, checks)

    for i in comparator:
        yield from i
