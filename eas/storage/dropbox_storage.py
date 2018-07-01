# -*- coding: utf-8 -*-

import contextlib
import time

import dropbox
import requests

from .exceptions import ControllerInterrupt, TemporaryStorageError
from .storage import Storage
from .limited_file import LimitedFile
from .stoppable_speed_limiter import StoppableSpeedLimiter
from .upload_task import UploadTask
from .download_task import DownloadTask
from ..common import get_file_size

UPLOAD_CHUNK_SIZE = 8 * 1024 ** 2 # Bytes
DOWNLOAD_CHUNK_SIZE = 16384
RETRY_CAUSES = {dropbox.exceptions.InternalServerError, requests.exceptions.RequestException}

__all__ = ["DropboxStorage"]

def _dropbox_meta_to_dict(meta):
    if isinstance(meta, dropbox.files.FileMetadata):
        return {"name":     meta.name,
                "type":     "file",
                "modified": meta.server_modified.timestamp(),
                "size":     meta.size,
                "mode":     None,
                "owner":    None,
                "group":    None,
                "link":     None}
    elif isinstance(meta, dropbox.files.FolderMetadata):
        return {"name":     meta.name,
                "type":     "dir",
                "modified": 0,
                "size":     0,
                "mode":     None,
                "owner":    None,
                "group":    None,
                "link":     None}
    else:
        if isinstance(meta, dropbox.files.Metadata):
            name = meta.name
        else:
            name = ""

        return {"name":     name,
                "type":     None,
                "modified": 0,
                "size":     0,
                "mode":     None,
                "owner":    None,
                "group":    None,
                "link":     None}

def auto_retry(attempt, n_retries, retry_interval):
    for i in range(n_retries + 1):
        try:
            return attempt()
        except Exception as e:
            if i == n_retries or not any(isinstance(e, j) for j in RETRY_CAUSES):
                raise e

        time.sleep(retry_interval)

class DropboxUploadTask(UploadTask):
    def __init__(self, config, dbx, in_file, out_path, **kwargs):
        in_file = LimitedFile(in_file, self, None)

        UploadTask.__init__(self, config, in_file, **kwargs)

        self.dbx = dbx
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

            file_size = get_file_size(self.in_file)

            def attempt():
                if self.stopped:
                    raise ControllerInterrupt

                if file_size <= UPLOAD_CHUNK_SIZE:
                    try:
                        self.dbx.files_upload(self.in_file.read(), self.out_path,
                                              mode=dropbox.files.WriteMode.overwrite)
                    except dropbox.exceptions.ApiError as e:
                        if not isinstance(e.error, dropbox.files.UploadError):
                            raise e

                        if not e.error.is_path():
                            raise e

                        reason = e.error.get_path().reason

                        if reason.is_conflict():
                            reason = reason.get_conflict()

                            if reason.is_folder():
                                raise IsADirectoryError(str(e))
                            elif reason.is_file_ancestor():
                                raise FileNotFoundError(str(e))

                            raise e
                        elif reason.is_no_write_permission():
                            raise PermissionError(str(e))

                        raise e

                    return

                chunk = self.in_file.read(UPLOAD_CHUNK_SIZE)
                result = self.dbx.files_upload_session_start(chunk)

                if self.stopped:
                    raise ControllerInterrupt

                cursor = dropbox.files.UploadSessionCursor(session_id=result.session_id,
                                                           offset=self.in_file.tell())
                commit_info = dropbox.files.CommitInfo(path=self.out_path,
                                                       mode=dropbox.files.WriteMode.overwrite)

                chunk = self.in_file.read(UPLOAD_CHUNK_SIZE)

                while len(chunk) >= UPLOAD_CHUNK_SIZE:
                    if self.stopped:
                        raise ControllerInterrupt

                    self.dbx.files_upload_session_append_v2(chunk, cursor)

                    chunk = self.in_file.read(UPLOAD_CHUNK_SIZE)

                if self.stopped:
                    raise ControllerInterrupt

                try:
                    self.dbx.files_upload_session_finish(chunk, cursor, commit_info)
                except dropbox.exceptions.ApiError as e:
                    if not isinstance(e.error, dropbox.files.UploadSessionFinishError):
                        raise e

                    if e.error.is_lookup_failed():
                        error = e.error.get_lookup_failed()

                        if error.is_not_found():
                            raise FileNotFoundError(str(e))

                        raise e
                    elif e.error.is_path():
                        error = e.error.get_path()

                        if error.is_conflict():
                            error = error.get_conflict()

                            if error.is_folder():
                                raise IsADirectoryError(str(e))
                            elif error.is_file_ancestor():
                                raise FileNotFoundError(str(e))

                            raise e
                        elif error.is_no_write_permission():
                            raise PermissionError(str(e))

                        raise e

                    raise e

            try:
                auto_retry(attempt, self.n_retries, 0.0)
            except Exception as e:
                if e in RETRY_CAUSES:
                    raise TemporaryStorageError(str(e))

                raise e

            self.status = "finished"
        except Exception as e:
            self.status = "failed"

            raise e

class DropboxDownloadTask(DownloadTask):
    def __init__(self, config, dbx, in_path, out_file, **kwargs):
        self.response = None
        self.speed_limiter = StoppableSpeedLimiter(None)

        DownloadTask.__init__(self, config, out_file, **kwargs)

        self.dbx = dbx
        self.in_path = in_path

    def __del__(self):
        if hasattr(DownloadTask, "__del__"):
            DownloadTask.__del__(self)

        if self.response is not None:
            self.response.close()

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
            if self.stopped:
                raise ControllerInterrupt

            try:
                self.response = self.dbx.files_download(self.in_path)[1]
            except dropbox.exceptions.ApiError as e:
                if not isinstance(e.error, dropbox.files.DownloadError):
                    raise e

                if not e.error.is_path():
                    raise e

                error = e.error.get_path()

                if error.is_not_found():
                    raise FileNotFoundError(str(e))

                raise e

            if self.stopped:
                raise ControllerInterrupt

            if self.response.status_code != 200:
                code = self.response.status
                self.response = None
                raise TemporaryStorageError("Unexpected status code: %s" % (code,))

            self.size = float(self.response.headers.get("Content-Length", "0"))

        if enable_retries:
            try:
                auto_retry(attempt, self.n_retries, 0.0)
            except Exception as e:
                if e in RETRY_CAUSES:
                    raise TemporaryStorageError(str(e))

                raise e
        else:
            attempt()

    def complete(self):
        try:
            self.status = "pending"

            def attempt():
                if self.stopped:
                    raise ControllerInterrupt

                self.begin(False)

                self.speed_limiter.begin()
                self.speed_limiter.quantity = 0

                with contextlib.closing(self.response):
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
                auto_retry(attempt, self.n_retries, 0.0)
            except Exception as e:
                if e in RETRY_CAUSES:
                    raise TemporaryStorageError(str(e))

                raise e

            self.status = "finished"
        except Exception as e:
            self.status = "failed"

            raise e

class DropboxStorage(Storage):
    name = "dropbox"
    type = "remote"
    case_sensitive = False
    parallelizable = True

    def __init__(self, config):
        Storage.__init__(self, config)

        token = config.encrypted_data.get("dropbox_token", "")
        self.dbx = dropbox.Dropbox(token)

    def get_meta(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        path = path.rstrip("/")

        if not path:
            return {"name":     "",
                    "type":     "dir",
                    "modified": 0,
                    "size":     0,
                    "mode":     None,
                    "owner":    None,
                    "group":    None,
                    "link":     None}

        def attempt():
            try:
                meta = self.dbx.files_get_metadata(path)
            except dropbox.exceptions.ApiError as e:
                if not isinstance(e.error, dropbox.files.GetMetadataError):
                    raise e

                if not e.error.is_path():
                    raise e

                error = e.error.get_path()

                if error.is_not_found():
                    raise FileNotFoundError(str(e))

                raise e

            return _dropbox_meta_to_dict(meta)

        try:
            return auto_retry(attempt, n_retries, 0.0)
        except Exception as e:
            if e in RETRY_CAUSES:
                raise TemporaryStorageError(str(e))

            raise e

    def listdir(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        path = path.rstrip("/")

        def attempt():
            try:
                response = self.dbx.files_list_folder(path)
            except dropbox.exceptions.ApiError as e:
                if not isinstance(e.error, dropbox.files.ListFolderError):
                    raise e

                if not e.error.is_path():
                    raise e

                error = e.error.get_path()

                if error.is_not_found():
                    raise FileNotFoundError(str(e))

                raise e

            for meta in response.entries:
                yield _dropbox_meta_to_dict(meta)

            while response.has_more:
                try:
                    response = self.dbx.files_list_folder_continue(response.cursor)
                except dropbox.exceptions.ApiError as e:
                    if not isinstance(e.error, dropbox.files.ListFolderContinueError):
                        raise e

                    if not e.error.is_path():
                        raise e

                    error = e.error.get_path()

                    if error.is_not_found():
                        raise FileNotFoundError(str(e))

                    raise e

                for meta in response.entries:
                    yield _dropbox_meta_to_dict(meta)

        try:
            return auto_retry(attempt, n_retries, 0.0)
        except Exception as e:
            if e in RETRY_CAUSES:
                raise TemporaryStorageError(str(e))

            raise e

    def mkdir(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        path = path.rstrip("/")

        def attempt():
            try:
                self.dbx.files_create_folder_v2(path)
            except dropbox.exceptions.ApiError as e:
                if not isinstance(e.error, dropbox.files.CreateFolderError):
                    raise e

                if not e.error.is_path():
                    raise e

                error = e.error.get_path()

                if error.is_conflict():
                    error = error.get_conflict()

                    if error.is_file() or error.is_folder():
                        raise FileExistsError(str(e))
                    elif error.is_file_ancestor():
                        raise FileNotFoundError(str(e))

                    raise e
                elif error.is_no_write_permission():
                    raise PermissionError(str(e))

                raise e

        try:
            auto_retry(attempt, n_retries, 0.0)
        except Exception as e:
            if e in RETRY_CAUSES:
                raise TemporaryStorageError(str(e))

            raise e

    def remove(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        path = path.rstrip("/")

        def attempt():
            try:
                self.dbx.files_delete_v2(path)
            except dropbox.exceptions.ApiError as e:
                if not isinstance(e.error, dropbox.files.DeleteError):
                    raise e

                if e.error.is_path_lookup():
                    error = e.error.get_path_lookup()

                    if error.is_not_found():
                        raise FileNotFoundError(str(e))

                    raise e
                elif e.error.is_path_write():
                    error = e.error.get_path_write()

                    if error.is_conflict():
                        error = error.get_conflict()

                        if error.is_file_ancestor():
                            raise FileNotFoundError(str(e))

                        raise e
                    elif error.is_no_write_permission():
                        raise PermissionError(str(e))

                    raise e

                raise e

        try:
            auto_retry(attempt, n_retries, 0.0)
        except Exception as e:
            if e in RETRY_CAUSES:
                raise TemporaryStorageError(str(e))

            raise e

    def download(self, in_path, out_file, **kwargs):
        return DropboxDownloadTask(self.config, self.dbx,
                                   in_path, out_file, **kwargs)

    def upload(self, in_file, out_path, **kwargs):
        out_path = out_path.rstrip("/")

        return DropboxUploadTask(self.config, self.dbx,
                                 in_file, out_path, **kwargs)

    def exists(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            self.get_meta(path, timeout, n_retries)

            return True
        except FileNotFoundError:
            return False

    def is_file(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            return self.get_meta(path, timeout, n_retries)["type"] == "file"
        except FileNotFoundError:
            return False

    def is_dir(self, path, timeout=None, n_retries=None):
        if timeout is None:
            timeout = self.config.timeout

        if n_retries is None:
            n_retries = self.config.n_retries

        try:
            return self.get_meta(path, timeout, n_retries)["type"] == "dir"
        except FileNotFoundError:
            return False
