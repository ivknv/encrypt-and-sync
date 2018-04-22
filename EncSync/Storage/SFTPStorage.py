# -*- coding: utf-8 -*-

import collections
import socket
import stat
import threading
import time

import paramiko
import pysftp

from .Storage import Storage
from .Exceptions import ControllerInterrupt, TemporaryStorageError
from .DownloadController import DownloadController
from .UploadController import UploadController
from .ControlledSpeedLimiter import ControlledSpeedLimiter

from .. import Paths
from ..LRUCache import LRUCache

__all__ = ["SFTPStorage"]

MIN_READ_SIZE = 4 * 1024**2 # Bytes

def auto_retry(attempt, n_retries, retry_interval):
    for i in range(n_retries + 1):
        try:
            return attempt()
        except socket.timeout:
            if i == n_retries:
                raise TemporaryStorageError("Socket timeout")
        except OSError as e:
            # This assumes that attempt() will try to establish a new connection
            if not str(e).startswith("Socket is closed"):
                raise e

            if i == n_retries:
                raise TemporaryStorageError(str(e))
        except paramiko.ssh_exception.SSHException as e:
            if type(e) is not paramiko.ssh_exception.SSHException:
                raise e

            if str(e).startswith("No hostkey for host "):
                raise e

            if i == n_retries:
                raise TemporaryStorageError(str(e))

        time.sleep(retry_interval)

class SFTPConnection(pysftp.Connection):
    def __init__(self, *args, **kwargs):
        # Fix for AttributeError on self.__del__()
        self._sftp_live = False
        self._transport = None
        self._cnopts = pysftp.CnOpts()

        pysftp.Connection.__init__(self, *args, **kwargs)

class SFTPUploadController(UploadController):
    def __init__(self, config, connection, in_file, out_path, **kwargs):
        self.speed_limiter = ControlledSpeedLimiter(self, None)
        UploadController.__init__(self, config, in_file, **kwargs)

        self.connection = connection
        self.out_path = out_path

    @property
    def limit(self):
        return self.speed_limiter.limit

    @limit.setter
    def limit(self, value):
        self.speed_limiter.limit = value

    def _work(self):
        if self.stopped:
            raise ControllerInterrupt

        with self.connection.open(self.out_path, "wb") as out_file:
            self.speed_limiter.begin()
            self.speed_limiter.quantity = 0

            while True:
                if self.stopped:
                    raise ControllerInterrupt

                content = self.in_file.read(MIN_READ_SIZE)

                if self.stopped:
                    raise ControllerInterrupt

                if not content:
                    break

                out_file.write(content)

                l = len(content)
                self.uploaded += l
                self.speed_limiter.quantity += l
                self.speed_limiter.delay()

    def work(self):
        auto_retry(self._work, self.n_retries, 0.0)

class SFTPDownloadController(DownloadController):
    def __init__(self, config, connection, in_path, out_file, **kwargs):
        self.speed_limiter = ControlledSpeedLimiter(self, None)

        DownloadController.__init__(self, config, out_file, **kwargs)

        self.in_path = in_path
        self.connection = connection

    @property
    def limit(self):
        return self.speed_limiter.limit

    @limit.setter
    def limit(self, value):
        self.speed_limiter.limit = value

    def begin(self, enable_retries=True):
        def attempt():
            if self.size is None:
                self.size = self.connection.stat(self.in_path).st_size

        if not enable_retries:
            attempt()
            return

        auto_retry(attempt, self.n_retries, 0.0)

    def _work(self):
        if self.stopped:
            raise ControllerInterrupt

        self.begin(False)

        if self.stopped:
            raise ControllerInterrupt

        with self.connection.open(self.in_path, "rb") as in_file:
            self.speed_limiter.begin()
            self.speed_limiter.quantity = 0

            while True:
                if self.stopped:
                    raise ControllerInterrupt

                content = in_file.read(MIN_READ_SIZE)

                if self.stopped:
                    raise ControllerInterrupt

                if not content:
                    break

                self.out_file.write(content)

                l = len(content)
                self.downloaded += l
                self.speed_limiter.quantity += l
                self.speed_limiter.delay()

    def work(self):
        auto_retry(self._work, self.n_retries, 0.0)

class SFTPStorage(Storage):
    name = "sftp"
    type = "remote"
    case_sensitive = True
    parallelizable = False

    @staticmethod
    def split_path(path):
        host_address, separator, path = path.lstrip("/").partition("/")
        path = Paths.join_properly("/", path) or "/"

        return host_address, path

    @staticmethod
    def split_host_address(address):
        username, user_separator, rest = address.partition("@")
        hostname, port_separator, port = rest.partition(":")

        if not username:
            raise ValueError("SFTP username must not be empty")

        if not hostname:
            raise ValueError("SFTP hostname cannot be empty")

        if port and not port_separator:
            raise ValueError("Invalid SFTP address: %r" % (address,))

        port = "22" if not port else port
        port = int(port)

        return username, hostname, port

    def get_connection(self, address):
        username, host, port = self.split_host_address(address)
        tid = threading.get_ident()
        connection = self._get_connection(username, host, port, tid)

        # Check if the connection is closed
        channel = connection.sftp_client.get_channel()

        if not channel.closed:
            return connection

        # Overwrite cache
        connection = self.make_connection(username, host, port, tid)
        self._get_connection.cache[((username, host, port, tid), ())] = connection

        return connection

    @LRUCache.decorate(max_size=1024)
    def _get_connection(self, username, host, port, tid):
        return self.make_connection(username, host, port, tid)

    def make_connection(self, username, host, port, tid):
        agent = paramiko.Agent()
        keys = agent.get_keys() + (None,)

        connection = None
        error = None

        for key in keys:
            try:
                connection = SFTPConnection(host, port=port, username=username,
                                            private_key=key)
            except paramiko.ssh_exception.AuthenticationException as e:
                error = e

        assert(connection is not None or error is not None)

        if connection is None:
            raise error

        if isinstance(self.config.timeout, collections.Iterable):
            connection.timeout = self.config.timeout[1]
        else:
            connection.timeout = self.config.timeout

        return connection

    def get_meta(self, path, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)
        hostname, sep, filename = path.partition("/")

        def attempt():
            connection = self.get_connection(host_address)

            s = connection.lstat(path)
            resource_type = None
            modified = 0
            size = 0
            real_path = None

            if stat.S_ISREG(s.st_mode):
                resource_type = "file"
                size = s.st_size
                modified = s.st_mtime
            elif stat.S_ISDIR(s.st_mode):
                resource_type = "dir"
                size = 0
                modified = 0

                if stat.S_ISLNK(s.st_mode):
                    real_path = connection.readlink(path)

            return {"type":     resource_type,
                    "name":     filename,
                    "modified": modified,
                    "size":     size,
                    "link":     real_path}

        return auto_retry(attempt, n_retries, 0.0)

    def listdir(self, path, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)

            # Using listdir_iter() for better memory usage
            for s in connection.sftp_client.listdir_iter(path):
                resource_type = None
                modified = 0
                size = 0
                real_path = None

                if stat.S_ISREG(s.st_mode):
                    resource_type = "file"
                    size = s.st_size
                    modified = s.st_mtime
                elif stat.S_ISDIR(s.st_mode):
                    resource_type = "dir"
                    size = 0
                    modified = 0

                    if stat.S_ISLNK(s.st_mode):
                        real_path = connection.readlink(path)

                yield {"type":     resource_type,
                       "name":     s.filename,
                       "modified": modified,
                       "size":     size,
                       "link":     real_path}

        return auto_retry(attempt, n_retries, 0.0)

    def mkdir(self, path, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)
            connection.mkdir(path)

        auto_retry(attempt, n_retries, 0.0)

    def remove(self, path, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)

            try:
                connection.rmdir(path)
                return
            except FileNotFoundError:
                # connection.rmdir(path) raises FileNotFoundError even if path exists but is a file
                connection.remove(path)
                return
            except OSError:
                # connection.rmdir(path) raises OSError when the directory is non-empty
                pass

            def recur(path):
                for s in connection.listdir_attr(path):
                    if not stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode):
                        connection.remove(Paths.join(path, s.filename))
                    else:
                        recur(Paths.join(path, s.filename))

                connection.rmdir(path)

            recur(path)

        auto_retry(attempt, n_retries, 0.0)

    def upload(self, in_file, out_path, **kwargs):
        n_retries = kwargs.get("n_retries")

        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, out_path = self.split_path(out_path)

        def attempt():
            return self.get_connection(host_address)

        connection = auto_retry(attempt, n_retries, 0.0)
        return SFTPUploadController(self.config, connection,
                                    in_file, out_path, **kwargs)

    def download(self, in_path, out_file, **kwargs):
        n_retries = kwargs.get("n_retries")

        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, in_path = self.split_path(in_path)

        def attempt():
            return self.get_connection(host_address)

        connection = auto_retry(attempt, n_retries, 0.0)
        return SFTPDownloadController(self.config, connection,
                                      in_path, out_file, **kwargs)

    def is_file(self, path, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)

            return connection.isfile(path)

        return auto_retry(attempt, n_retries, 0.0)

    def is_dir(self, path, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)

            return connection.isdir(path)

        return auto_retry(attempt, n_retries, 0.0)

    def exists(self, path, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)

            return connection.exists(path)

        return auto_retry(attempt, n_retries, 0.0)
