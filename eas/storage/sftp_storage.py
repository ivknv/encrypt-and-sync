# -*- coding: utf-8 -*-

import collections
from datetime import datetime, timezone
import socket
import stat
import threading
import time

import paramiko
import pysftp

from .storage import Storage
from .exceptions import ControllerInterrupt, TemporaryStorageError
from .download_task import DownloadTask
from .upload_task import UploadTask
from .stoppable_speed_limiter import StoppableSpeedLimiter

from .. import pathm
from ..common import LRUCache
from ..constants import PERMISSION_MASK

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

            if str(e).startswith("not a valid DSA"):
                raise e

            if i == n_retries:
                raise TemporaryStorageError(str(e))

        time.sleep(retry_interval)

def utc_to_local(utc_timestamp):
    return datetime.fromtimestamp(utc_timestamp).replace(tzinfo=timezone.utc).astimezone(tz=None).timestamp()

def local_to_utc(local_timestamp):
    try:
        return max(time.mktime(time.gmtime(local_timestamp)), 0)
    except (OSError, OverflowError):
        return 0

class SFTPConnection(pysftp.Connection):
    def __init__(self, *args, **kwargs):
        # Fix for AttributeError on self.__del__()
        self._sftp_live = False
        self._transport = None
        self._cnopts = pysftp.CnOpts()

        pysftp.Connection.__init__(self, *args, **kwargs)

class SFTPUploadTask(UploadTask):
    def __init__(self, config, storage, in_file, out_path, **kwargs):
        self.speed_limiter = StoppableSpeedLimiter(None)
        UploadTask.__init__(self, config, in_file, **kwargs)

        self.storage = storage
        self.out_path = out_path

    @property
    def limit(self):
        return self.speed_limiter.limit

    @limit.setter
    def limit(self, value):
        self.speed_limiter.limit = value

    def stop(self):
        super().stop()

        self.speed_limiter.stop()

    def _complete(self):
        if self.stopped:
            raise ControllerInterrupt

        host_address, out_path = self.storage.split_path(self.out_path)
        connection = self.storage.get_connection(host_address)

        with connection.open(out_path, "wb") as out_file:
            out_file.set_pipelined(True)
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

    def complete(self):
        try:
            self.status = "pending"

            auto_retry(self._complete, self.n_retries, 0.0)

            self.status = "finished"
        except Exception as e:
            self.status = "failed"

            raise e

class SFTPDownloadTask(DownloadTask):
    def __init__(self, config, storage, in_path, out_file, **kwargs):
        self.speed_limiter = StoppableSpeedLimiter(None)

        DownloadTask.__init__(self, config, out_file, **kwargs)

        self.in_path = in_path
        self.storage = storage

    @property
    def limit(self):
        return self.speed_limiter.limit

    @limit.setter
    def limit(self, value):
        self.speed_limiter.limit = value

    def stop(self):
        super().stop()

        self.speed_limiter.stop()

    def begin(self, enable_retries=True):
        def attempt():
            if self.size is None:
                host_address, in_path = self.storage.split_path(self.in_path)
                connection = self.storage.get_connection(host_address)

                self.size = connection.stat(in_path).st_size

        if not enable_retries:
            attempt()
            return

        auto_retry(attempt, self.n_retries, 0.0)

    def _complete(self):
        if self.stopped:
            raise ControllerInterrupt

        self.begin(False)

        if self.stopped:
            raise ControllerInterrupt

        host_address, in_path = self.storage.split_path(self.in_path)
        connection = self.storage.get_connection(host_address)

        with connection.open(in_path, "rb") as in_file:
            in_file.set_pipelined(True)
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

    def complete(self):
        try:
            self.status = "pending"

            auto_retry(self._complete, self.n_retries, 0.0)

            self.status = "finished"
        except Exception as e:
            self.status = "failed"

            raise e

class SFTPStorage(Storage):
    name = "sftp"
    type = "remote"
    case_sensitive = True
    parallelizable = False
    persistent_mode = True

    supports_set_modified = True
    supports_chmod = True
    supports_chown = True
    supports_symlinks = True

    @staticmethod
    def split_path(path):
        host_address, separator, path = path.lstrip("/").partition("/")
        path = pathm.join_properly("/", path) or "/"

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

    def get_secondary_connection(self, address):
        username, host, port = self.split_host_address(address)
        tid = threading.get_ident()
        connection = self._get_secondary_connection(username, host, port, tid)

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

    @LRUCache.decorate(max_size=1024)
    def _get_secondary_connection(self, username, host, port, tid):
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
                break
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
        hostname, sep, filename = path.rpartition("/")

        def attempt():
            connection = self.get_connection(host_address)

            s = connection.lstat(path)
            resource_type = None
            modified = 0
            size = 0
            link_path = None

            if stat.S_ISREG(s.st_mode):
                resource_type = "file"
                size = s.st_size
            elif stat.S_ISDIR(s.st_mode):
                resource_type = "dir"
                size = 0
            elif stat.S_ISLNK(s.st_mode):
                resource_type = "file"

                # connection.readlink() will always return absolute path, we don't want that
                link_path = connection.sftp_client.readlink(path)

            modified = local_to_utc(s.st_mtime)
            mode = s.st_mode & PERMISSION_MASK
            owner = s.st_uid
            group = s.st_gid

            return {"type":     resource_type,
                    "name":     filename,
                    "modified": modified,
                    "size":     size,
                    "mode":     mode,
                    "owner":    owner,
                    "group":    group,
                    "link":     link_path}

        return auto_retry(attempt, n_retries, 0.0)

    def listdir(self, path, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)
            secondary_connection = self.get_secondary_connection(host_address)

            # Using listdir_iter() for better memory usage
            for s in connection.sftp_client.listdir_iter(path):
                resource_type = None
                modified = 0
                size = 0
                link_path = None

                if stat.S_ISREG(s.st_mode):
                    resource_type = "file"
                    size = s.st_size
                elif stat.S_ISDIR(s.st_mode):
                    resource_type = "dir"
                    size = 0

                try:
                    # listdir_iter() appears to always follow symlinks :(
                    link_path = secondary_connection.sftp_client.readlink(pathm.join(path, s.filename))
                    resource_type = "file"
                except OSError:
                    pass

                modified = local_to_utc(s.st_mtime)
                mode = s.st_mode & PERMISSION_MASK
                owner = s.st_uid
                group = s.st_gid

                yield {"type":     resource_type,
                       "name":     s.filename,
                       "modified": modified,
                       "size":     size,
                       "mode":     mode,
                       "owner":    owner,
                       "group":    group,
                       "link":     link_path}

        return auto_retry(attempt, n_retries, 0.0)

    def mkdir(self, path, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)

            try:
                connection.mkdir(path)
            except OSError as e:
                if str(e) == "Failure":
                    raise FileExistsError("Path already exists")

                raise e

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
                        connection.remove(pathm.join(path, s.filename))
                    else:
                        recur(pathm.join(path, s.filename))

                connection.rmdir(path)

            recur(path)

        auto_retry(attempt, n_retries, 0.0)

    def upload(self, in_file, out_path, **kwargs):
        return SFTPUploadTask(self.config, self, in_file, out_path, **kwargs)

    def download(self, in_path, out_file, **kwargs):
        return SFTPDownloadTask(self.config, self, in_path, out_file, **kwargs)

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

    def set_modified(self, path, new_modified, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        new_modified = utc_to_local(new_modified)

        def attempt():
            connection = self.get_connection(host_address)

            # It always follows symlinks :(
            if stat.S_ISLNK(connection.lstat(path).st_mode):
                return

            connection.sftp_client.utime(path, (new_modified, new_modified))

        auto_retry(attempt, n_retries, 0.0)

    def chmod(self, path, mode, n_retries=None, timeout=None):
        if mode is None:
            return

        mode = pysftp.st_mode_to_int(mode)

        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)

            # It always follows symlinks :(
            if stat.S_ISLNK(connection.lstat(path).st_mode):
                return

            connection.chmod(path, mode)

        auto_retry(attempt, n_retries, 0.0)

    def chown(self, path, uid, gid, n_retries=None, timeout=None):
        if uid is None and gid is None:
            return

        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)

            # It always follows symlinks :(
            if stat.S_ISLNK(connection.lstat(path).st_mode):
                return

            connection.chown(path, uid, gid)

        auto_retry(attempt, n_retries, 0.0)

    def create_symlink(self, path, link_path, n_retries=None, timeout=None):
        if n_retries is None:
            n_retries = self.config.n_retries

        host_address, path = self.split_path(path)

        def attempt():
            connection = self.get_connection(host_address)

            connection.symlink(link_path, path)

        auto_retry(attempt, n_retries, 0.0)
