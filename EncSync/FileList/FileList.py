#!/usr/bin/env python
# -*- coding: utf-8 -*-

class FileList(object):
    def create(self):
        raise NotImplementedError

    def insert_node(self, node):
        raise NotImplementedError

    def remove_node(self, path):
        raise NotImplementedError

    def remove_node_children(self, path):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def find_node(self, path):
        raise NotImplementedError

    def find_node_children(self, path):
        raise NotImplementedError

    def select_all_nodes(self):
        raise NotImplementedError

    def insert_nodes(self, nodes):
        for i in nodes:
            self.insert_node(i)
