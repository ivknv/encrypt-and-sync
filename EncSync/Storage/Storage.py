# -*- coding: utf-8 -*-

__all__ = ["Storage"]

class Storage(object):
    """
        Implements storage API.

        :param encsync: `EncSync` instance

        :cvar name: `str`, storage name
        :cvar case_sensitive: `bool`, determines whether the storage filenames are case sensitive
        :cvar parallelizable: `bool`, determines whether the storage supports parallel operations
                              (or at least if it's useful or not)
        :ivar encsync: `EncSync` instance
    """

    name = None
    case_sensitive = True
    parallelizable = False

    def __init__(self, encsync):
        self.encsync = encsync

    def get_meta(self, path, timeout=float("inf"), n_retries=0):
        """
            Get metadata of `path`.

            :param path: path to get the metadata of
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :returns: The result should be a `dict` of the following form:
                      {"name":     <filename>
                       "type":     <"file" or "dir">,
                       "modified": <modified date, timestamp in UTC, `int` or `float`>,
                       "size":     <file size, `int`, 0 if not a file>,
                       "link":     <real path or None>}
                      It doesn't have to be exactly the same, it can have any extra keys,
                      this is just the minimum.
        """

        raise NotImplementedError

    def listdir(self, path, timeout=float("inf"), n_retries=0):
        """
            Get contents of `path`.

            :param path: path to the directory to list
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :returns: iterable of `dict` containing metadata
        """

        raise NotImplementedError

    def mkdir(self, path, timeout=float("inf"), n_retries=0):
        """
            Create a new directory.

            :param path: path of the directory to create
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries
        """
        
        raise NotImplementedError

    def remove(self, path, timeout=float("inf"), n_retries=0):
        """
            Remove `path`.

            :param path: path to remove
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries
        """

        raise NotImplementedError

    def upload(self, in_file, out_path, timeout=float("inf"), n_retries=0):
        """
            Upload a new file at `out_path`.

            :param in_file: file-like object to upload
            :param out_path: destination path
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :returns: `UploadController`
        """

        raise NotImplementedError

    def download(self, in_path, out_file, timeout=float("inf"), n_retries=0):
        """
            Download `in_path` into `out_file`.

            :param in_path: path to download from
            :param out_file: file-like object to download into
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :param: `DownloadController`
        """

        raise NotImplementedError

    def is_file(self, path, timeout=float("inf"), n_retries=0):
        """
            Check whether `path` is a file.

            :param path: path to check
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :returns: `bool`
        """

        raise NotImplementedError

    def is_dir(self, path, timeout=float("inf"), n_retries=0):
        """
            Check whether `path` is a directory.

            :param path: path to check
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :returns: `bool`
        """

        raise NotImplementedError

    def exists(self, path, timeout=float("inf"), n_retries=0):
        """
            Check whether `path` exists.

            :param path: path to check
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :returns: `bool`
        """

        raise NotImplementedError
