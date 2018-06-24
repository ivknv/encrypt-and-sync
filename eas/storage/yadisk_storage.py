# -*- coding: utf-8 -*-

from io import BytesIO

import time

from requests.exceptions import RequestException
import yadisk.settings
from yadisk.exceptions import PathNotFoundError, DirectoryExistsError
from yadisk.exceptions import RetriableYaDiskError, WrongResourceTypeError
import yadisk.utils

from ..constants import YADISK_APP_ID, YADISK_APP_SECRET

from .stoppable_speed_limiter import StoppableSpeedLimiter
from .limited_file import LimitedFile
from .storage import Storage
from .exceptions import ControllerInterrupt, TemporaryStorageError
from .download_task import DownloadTask
from .upload_task import UploadTask

__all__ = ["YaDiskStorage"]

DOWNLOAD_CHUNK_SIZE = 16384

def _yadisk_meta_to_dict(meta):
    properties = meta.custom_properties or {}

    mode = properties.get("eas_file_mode")
    owner = properties.get("eas_file_owner")
    group = properties.get("eas_file_group")
    modified = properties.get("eas_modified")
    link_path = properties.get("eas_link_path")

    if not isinstance(modified, (int, float)):
        try:
            modified = time.mktime(meta.modified.utctimetuple())
            modified = max(modified, 0)
        except (OSError, OverflowError):
            modified = 0

    mode      = None if not isinstance(mode,      int) else mode
    owner     = None if not isinstance(owner,     int) else owner
    group     = None if not isinstance(group,     int) else group
    link_path = None if not isinstance(link_path, str) else link_path

    return {"type":     meta.type,
            "name":     meta.name,
            "modified": modified,
            "size":     meta.size if meta.type != "dir" else 0,
            "mode":     mode,
            "owner":    owner,
            "group":    group,
            "link":     link_path}

class YaDiskDownloadTask(DownloadTask):
    def __init__(self, config, ynd, in_path, out_file, **kwargs):
        self.speed_limiter = StoppableSpeedLimiter(None)

        DownloadTask.__init__(self, config, out_file, **kwargs)

        self.in_path = in_path
        self.link = None
        self.response = None
        self.yadisk = ynd

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
        if self.stopped:
            raise ControllerInterrupt

        def attempt():
            if self.stopped:
                raise ControllerInterrupt

            self.link = self.yadisk.get_download_link(self.in_path,
                                                      timeout=self.timeout,
                                                      n_retries=0)

            if self.stopped:
                raise ControllerInterrupt

            self.response = self.yadisk.make_session().get(self.link, stream=True,
                                                           timeout=self.timeout,
                                                           headers={"Connection": "close"})

            if self.response.status_code != 200:
                self.response, response = None, self.response
                raise yadisk.utils.get_exception(response)

            self.size = float(self.response.headers.get("Content-Length", "0"))

        if enable_retries:
            try:
                yadisk.utils.auto_retry(attempt, self.n_retries, 0.0)
            except PathNotFoundError as e:
                raise FileNotFoundError(str(e))
            except (RetriableYaDiskError, RequestException) as e:
                raise TemporaryStorageError(str(e))
        else:
            attempt()

    def complete(self):
        try:
            self.status = "pending"

            if self.stopped:
                raise ControllerInterrupt

            def attempt():
                if self.stopped:
                    raise ControllerInterrupt

                self.begin(False)

                if self.stopped:
                    raise ControllerInterrupt

                self.speed_limiter.begin()
                self.speed_limiter.quantity = 0

                for chunk in self.response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if self.stopped:
                        raise ControllerInterrupt

                    if not chunk:
                        continue

                    self.out_file.write(chunk)
                    l = len(chunk)
                    self.downloaded += l
                    self.speed_limiter.quantity += l

                    if self.stopped:
                        raise ControllerInterrupt

                    self.speed_limiter.delay()

                    if self.stopped:
                        raise ControllerInterrupt

                self.response = None

            try:
                yadisk.utils.auto_retry(attempt, self.n_retries, 0.0)
            except PathNotFoundError as e:
                raise FileNotFoundError(str(e))
            except (RetriableYaDiskError, RequestException) as e:
                raise TemporaryStorageError(str(e))

            self.status = "finished"
        except Exception as e:
            self.status = "failed"

            raise e

class YaDiskUploadTask(UploadTask):
    def __init__(self, config, ynd, in_file, out_path, **kwargs):
        in_file = LimitedFile(in_file, self, None)

        UploadTask.__init__(self, config, in_file, **kwargs)

        self.yadisk = ynd
        self.out_path = out_path

    @property
    def limit(self):
        return self.in_file.limit

    @limit.setter
    def limit(self, value):
        self.in_file.limit = value

    def stop(self):
        super().stop()

        self.in_file.stop()

    def complete(self):
        try:
            self.status = "pending"

            if self.stopped:
                raise ControllerInterrupt

            try:
                self.yadisk.upload(self.in_file, self.out_path, overwrite=True,
                                   timeout=self.timeout, n_retries=self.n_retries,
                                   retry_interval=3.0)
            except PathNotFoundError as e:
                raise FileNotFoundError(str(e))
            except (RetriableYaDiskError, RequestException) as e:
                raise TemporaryStorageError(str(e))

            self.status = "finished"
        except Exception as e:
            self.status = "failed"

            raise e

class YaDiskStorage(Storage):
    name = "yadisk"
    type = "remote"
    case_sensitive = True
    parallelizable = True

    supports_set_modified = True
    supports_chmod = True
    supports_chown = True
    supports_symlinks = True

    def __init__(self, config):
        Storage.__init__(self, config)

        token = config.encrypted_data.get("yadisk_token", "")

        self.yadisk = yadisk.YaDisk(YADISK_APP_ID, YADISK_APP_SECRET, token)

    def get_meta(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            meta = self.yadisk.get_meta(path, timeout=timeout, n_retries=n_retries)
        except PathNotFoundError as e:
            raise FileNotFoundError(str(e))
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

        return _yadisk_meta_to_dict(meta)

    def listdir(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            contents = self.yadisk.listdir(path, timeout=timeout, n_retries=n_retries)

            for i in contents:
                yield _yadisk_meta_to_dict(i)
        except PathNotFoundError as e:
            raise FileNotFoundError(str(e))
        except WrongResourceTypeError as e:
            raise NotADirectoryError(str(e))
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

    def mkdir(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            self.yadisk.mkdir(path, timeout=timeout, n_retries=n_retries)
        except PathNotFoundError as e:
            raise FileNotFoundError(str(e))
        except DirectoryExistsError as e:
            raise FileExistsError(str(e))
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

    def remove(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            self.yadisk.remove(path, timeout=timeout, n_retries=n_retries)
        except PathNotFoundError as e:
            raise FileNotFoundError(str(e))
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

    def upload(self, in_file, out_path, **kwargs):
        return YaDiskUploadTask(self.config, self.yadisk,
                                in_file, out_path, **kwargs)

    def download(self, in_path, out_file, **kwargs):
        return YaDiskDownloadTask(self.config, self.yadisk,
                                  in_path, out_file, **kwargs)

    def is_file(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            return self.yadisk.is_file(path, timeout=timeout, n_retries=n_retries)
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

    def is_dir(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            return self.yadisk.is_dir(path, timeout=timeout, n_retries=n_retries)
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

    def exists(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            return self.yadisk.exists(path, timeout=timeout, n_retries=n_retries)
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

    def set_modified(self, path, modified, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            self.yadisk.patch(path, {"eas_modified": modified},
                              timeout=timeout, n_retries=n_retries)
        except PathNotFoundError as e:
            raise FileNotFoundError(str(e))
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

    def chmod(self, path, mode, timeout=None, n_retries=None):
        if mode is None:
            return

        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            self.yadisk.patch(path, {"eas_file_mode": mode},
                              timeout=timeout, n_retries=n_retries)
        except PathNotFoundError as e:
            raise FileNotFoundError(str(e))
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

    def chown(self, path, uid, gid, timeout=None, n_retries=None):
        if uid is None and gid is None:
            return

        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        ownership = {}

        if uid is not None:
            ownership["eas_file_owner"] = uid

        if gid is not None:
            ownership["eas_file_group"] = gid

        assert(ownership)

        try:
            self.yadisk.patch(path, ownership, timeout=timeout, n_retries=n_retries)
        except PathNotFoundError as e:
            raise FileNotFoundError(str(e))
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

    def create_symlink(self, path, link_path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        first_try = True

        def attempt():
            nonlocal first_try

            # Avoid overwriting existing files
            if first_try:
                self.yadisk.upload(BytesIO(), path, timeout=timeout, n_retries=0)
                first_try = False

            self.yadisk.patch(path, {"eas_link_path": link_path},
                              timeout=timeout, n_retries=0)

        try:
            yadisk.utils.auto_retry(attempt, n_retries, 0.0)
        except PathNotFoundError as e:
            raise FileNotFoundError(str(e))
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))
