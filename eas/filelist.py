import sqlite3
from . import cdb, pathm, encryption
                                        uid INTEGER,
                                        gid INTEGER,
                                        link_path TEXT,
        node["path"] = prepare_path(node["path"])

        node.setdefault("mode", None)
        node.setdefault("owner", None)
        node.setdefault("group", None)
        node.setdefault("link_path", None)

                                                        mode, uid, gid, path,
                                                        link_path, IVs)
                                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                 node["owner"],
                                 node["group"],
                                 node["path"],
                                 node["link_path"],
            self.connection.execute("""SELECT type, modified, padded_size, mode,
                                              uid, gid, path, link_path, IVs
            self.connection.execute("""SELECT type, modified, padded_size, mode,
                                              uid, gid, path, link_path, IVs
            :param mode: `int` or `None`, new file mode
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
                                   VALUES(?, ?, ?, ?)""", ("v", path, ivs, format_timestamp(0)))

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
