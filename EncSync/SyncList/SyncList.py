#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .LocalFileList import LocalFileList
from .RemoteFileList import RemoteFileList

class SyncList(object):
    def __init__(self):
        self.local = LocalFileList()
        self.remote = RemoteFileList()

    def time_since_last_commit(self):
        return min((self.local.conn.time_since_last_commit(),
                    self.remote.conn.time_since_last_commit()))

    def __enter__(self):
        self.local.__enter__()
        self.remote.__enter__()

    def __exit__(self, *args, **kwargs):
        self.local.__exit__(*args, **kwargs)
        self.remote.__exit__(*args, **kwargs)

    def create(self):
        self.local.create()
        self.remote.create()

    def insert_local_node(self, node):
        self.local.insert_node(node)

    def insert_remote_node(self, node):
        self.remote.insert_node(node)

    def update_local_size(self, path, new_size):
        self.local.update_size(path, new_size)

    def remove_local_node(self, path):
        self.local.remove_node(path)

    def remove_remote_node(self, path):
        self.remote.remove_node(path)

    def remove_local_node_children(self, path):
        self.local.remove_node_children(path)

    def remove_remote_node_children(self, path):
        self.remote.remove_node_children(path)

    def clear_local(self):
        self.local.clear()

    def clear_remote(self):
        self.remote.clear()

    def find_local_node(self, path):
        return self.local.find_node(path)

    def find_remote_node(self, path):
        return self.remote.find_node(path)

    def find_local_node_children(self, path):
        return self.local.find_node_children(path)

    def find_remote_node_children(self, path):
        return self.remote.find_node_children(path)

    def select_all_local_nodes(self):
        return self.local.select_all_nodes()

    def select_all_remote_nodes(self):
        return self.remote.select_all_nodes()

    def insert_local_nodes(self, nodes):
        self.local.insert_nodes(nodes)

    def insert_remote_nodes(self, nodes):
        self.remote.insert_nodes(nodes)

    def is_remote_list_empty(self, parent_dir):
        return self.remote.is_empty(parent_dir)

    def get_remote_file_count(self, parent_dir):
        return self.remote.get_file_count(parent_dir)

    def begin_transaction(self, *args, **kwargs):
        self.local.begin_transaction(*args, **kwargs)
        self.remote.begin_transaction(*args, **kwargs)

    def commit(self):
        self.local.commit()
        self.remote.commit()

    def seamless_commit(self):
        self.local.conn.seamless_commit()
        self.remote.conn.seamless_commit()

    def rollback(self):
        self.local.rollback()
        self.remote.rollback()

    def close(self):
        self.local.close()
        self.remote.close()
