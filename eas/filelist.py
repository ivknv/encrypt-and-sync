    return pathm.dir_denormalize(pathm.join_properly("/", path))
        path = pathm.dir_normalize(prepare_path(path))
        parent_dir = pathm.dir_normalize(prepare_path(path))
            Update node's size.
        path = prepare_path(path)

    def update_modified(self, path, modified):
        """
            Update node's modified date.

            :param path: path of the node
            :param modified: new modified date
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)

        modified = format_timestamp(modified)

        self.connection.execute("UPDATE filelist SET modified=? WHERE path=? or path=?",
                                (modified, path, path_n))

    def update_mode(self, path, mode):
        """
            Update node's mode.

            :param path: path of the node
            :param mode: `int`, new file mode
        """

        path = prepare_path(path)
        path_n = pathm.dir_normalize(path)

        self.connection.execute("UPDATE filelist SET mode=? WHERE path=? or path=?",
                                (mode, path, path_n))
