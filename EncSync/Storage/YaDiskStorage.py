# -*- coding: utf-8 -*-

import time

from requests.exceptions import RequestException
import yadisk.settings
from yadisk.exceptions import PathNotFoundError, DirectoryExistsError
from yadisk.exceptions import RetriableYaDiskError, WrongResourceTypeError
import yadisk.utils

from ..constants import YADISK_APP_ID, YADISK_APP_SECRET

from .ControlledSpeedLimiter import ControlledSpeedLimiter
from .LimitedFile import LimitedFile
from .Storage import Storage
from .Exceptions import ControllerInterrupt, TemporaryStorageError
from .DownloadController import DownloadController
from .UploadController import UploadController

__all__ = ["YaDiskStorage"]

DOWNLOAD_CHUNK_SIZE = 16384

def _yadisk_meta_to_dict(meta):
    try:
        modified = time.mktime(meta.modified.utctimetuple())
        modified = max(modified, 0)
    except (OSError, OverflowError):
        modified = 0

    return {"type":     meta.type,
            "name":     meta.name,
            "modified": modified,
            "size":     meta.size if meta.type != "dir" else 0,
            "link":     None}

class YaDiskDownloadController(DownloadController):
    def __init__(self, ynd, in_path, out_file, limit=float("inf"), timeout=None, n_retries=None):
        self.speed_limiter = ControlledSpeedLimiter(self, limit)

        DownloadController.__init__(self, out_file, limit)

        self.in_path = in_path
        self.link = None
        self.response = None
        self.yadisk = ynd
        self.timeout = timeout
        self.n_retries = n_retries

    @property
    def limit(self):
        return self.speed_limiter.limit

    @limit.setter
    def limit(self, value):
        self.speed_limiter.limit = value

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
                                                           timeout=self.timeout)

            if self.response.status_code != 200:
                self.response = None
                raise yadisk.utils.get_exception(self.response)

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

    def work(self):
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

class YaDiskUploadController(UploadController):
    def __init__(self, ynd, in_file, out_path, limit=float("inf"), timeout=None, n_retries=None):
        in_file = LimitedFile(in_file, self, limit)
        UploadController.__init__(self, in_file, limit)

        self.yadisk = ynd
        self.out_path = out_path
        self.timeout = timeout

        self.n_retries = n_retries

    @property
    def limit(self):
        return self.in_file.limit

    @limit.setter
    def limit(self, value):
        self.in_file.limit = value

    def work(self):
        if self.stopped:
            raise ControllerInterrupt

        try:
            def attempt():
                self.yadisk.upload(self.in_file, self.out_path, overwrite=True,
                                   timeout=self.timeout, n_retries=0)

            yadisk.utils.auto_retry(attempt, self.n_retries, 0.0)
        except PathNotFoundError as e:
            raise FileNotFoundError(str(e))
        except (RetriableYaDiskError, RequestException) as e:
            raise TemporaryStorageError(str(e))

class YaDiskStorage(Storage):
    name = "yadisk"
    case_sensitive = True
    parallelizable = True

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

    def upload(self, in_file, out_path, timeout=None, n_retries=None, limit=None):
        if limit is None:
            limit = self.config.upload_limit

        if n_retries is None:
            n_retries = self.config.n_retries

        if timeout is None:
            timeout = self.config.upload_timeout

        controller = YaDiskUploadController(self.yadisk, in_file, out_path,
                                            limit, timeout, n_retries)

        return controller

    def download(self, in_path, out_file, timeout=None, n_retries=None, limit=None):
        if limit is None:
            limit = self.config.download_limit

        if n_retries is None:
            n_retries = self.config.n_retries

        if timeout is None:
            timeout = self.config.timeout

        controller = YaDiskDownloadController(self.yadisk, in_path, out_file,
                                              limit, timeout, n_retries)

        return controller

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
