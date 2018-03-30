# -*- coding: utf-8 -*-

import re

from .Exceptions import UnknownStorageError

__all__ = ["Storage"]

_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9-_.]{0,63}$")

class Storage(object):
    """
        Implements storage API.

        :param config: `config` instance

        :cvar registered_storages: `dict`, contains descendant storage classes (don't touch it!)

        :cvar name: `str`, storage name, must match ^[a-zA-Z0-9_][a-zA-Z0-9-_.]{0,63}$
        :cvar type: `str`, storage type ("local" or "remote")
        :cvar case_sensitive: `bool`, determines whether the storage filenames are case sensitive
        :cvar parallelizable: `bool`, determines whether the storage supports parallel operations
                              (or at least if it's useful or not)
        :ivar config: `Config` instance
    """

    registered_storages = {}

    name = None
    type = None
    case_sensitive = True
    parallelizable = False

    @classmethod
    def validate(cls):
        """
            Validate the storage class.

            :raises ValuError: invalid storage class
        """

        if not isinstance(cls.name, str) or not cls.name:
            raise ValueError("Storage name must be a non-empty string (got %r)" % (type(cls.name),))

        if not _NAME_REGEX.match(cls.name):
            raise ValueError("Invalid storage name: %r" % (cls.name,))

        if cls.type not in ("local", "remote"):
            raise ValueError("Invalid storage type: %r" % (cls.type,))

        if not isinstance(cls.case_sensitive, bool):
            raise ValueError("%s.case_sensitive must be of type bool" % (cls.__name__,))

        if not isinstance(cls.parallelizable, bool):
            raise ValueError("%s.parallelizable must be of type bool" % (cls.__name__,))

    @classmethod
    def register(cls):
        """
            Register the descendant storage class.
            
            :raises ValueError: invalid storage class
        """

        cls.validate()
        Storage.registered_storages[cls.name] = cls

    @classmethod
    def unregister(cls):
        """
            Unregister the descendant storage class.
            
            :raises UnknownStorageError: attempting to unregister an unregistered storage
        """

        try:
            Storage.registered_storages.pop(cls.name)
        except KeyError:
            raise UnknownStorageError("unregistered storage %r" % (cls.name,))

    @staticmethod
    def get_storage(name):
        """
            Get a (registered) storage class by name.

            :param name: `str`, storage name

            :raises UnknownStorageError: requested storage is not registered

            :returns: corresponding `Storage`-based class
        """

        try:
            return Storage.registered_storages[name]
        except KeyError:
            raise UnknownStorageError("unregistered storage %r" % (name,))

    def __init__(self, config):
        self.config = config

    def get_meta(self, path, timeout=float("inf"), n_retries=0):
        """
            Get metadata of `path`.

            :param path: path to get the metadata of
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :raises IOError: in case of I/O errors
            :raises TemporaryStorageError: in case of temporary I/O errors

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

            :raises IOError: in case of I/O errors
            :raises TemporaryStorageError: in case of temporary I/O errors

            :returns: iterable of `dict` containing metadata
        """

        raise NotImplementedError

    def mkdir(self, path, timeout=float("inf"), n_retries=0):
        """
            Create a new directory.

            :param path: path of the directory to create
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :raises IOError: in case of I/O errors
            :raises TemporaryStorageError: in case of temporary I/O errors
        """
        
        raise NotImplementedError

    def remove(self, path, timeout=float("inf"), n_retries=0):
        """
            Remove `path`.

            :param path: path to remove
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :raises IOError: in case of I/O errors
            :raises TemporaryStorageError: in case of temporary I/O errors
        """

        raise NotImplementedError

    def upload(self, in_file, out_path,
               timeout=float("inf"), n_retries=0, limit=float("inf")):
        """
            Upload a new file at `out_path`.

            :param in_file: file-like object to upload
            :param out_path: destination path
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries
            :param limit: `float`, speed limit (bytes per second)

            :returns: `UploadController`
        """

        raise NotImplementedError

    def download(self, in_path, out_file,
                 timeout=float("inf"), n_retries=0, limit=float("inf")):
        """
            Download `in_path` into `out_file`.

            :param in_path: path to download from
            :param out_file: file-like object to download into
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries
            :param limit: `float`, speed limit (bytes per second)

            :param: `DownloadController`
        """

        raise NotImplementedError

    def is_file(self, path, timeout=float("inf"), n_retries=0):
        """
            Check whether `path` is a file.

            :param path: path to check
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :raises IOError: in case of I/O errors
            :raises TemporaryStorageError: in case of temporary I/O errors

            :returns: `bool`
        """

        raise NotImplementedError

    def is_dir(self, path, timeout=float("inf"), n_retries=0):
        """
            Check whether `path` is a directory.

            :param path: path to check
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :raises IOError: in case of I/O errors
            :raises TemporaryStorageError: in case of temporary I/O errors

            :returns: `bool`
        """

        raise NotImplementedError

    def exists(self, path, timeout=float("inf"), n_retries=0):
        """
            Check whether `path` exists.

            :param path: path to check
            :param timeout: `int` or `float`, timeout for the operation
            :param n_retries: `int`, maximum number of retries

            :raises IOError: in case of I/O errors
            :raises TemporaryStorageError: in case of temporary I/O errors

            :returns: `bool`
        """

        raise NotImplementedError
