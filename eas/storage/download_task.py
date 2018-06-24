# -*- coding: utf-8 -*-

from ..task import Task

__all__ = ["DownloadTask"]

class DownloadTask(Task):
    """
        Events: downloaded_changed
    """

    def __init__(self, config, out_file, limit=None, timeout=None, n_retries=None):
        super().__init__()

        self.config = config
        self.out_file = out_file
        self._downloaded = 0
        self.size = None

        if limit is None:
            limit = config.download_limit

        if timeout is None:
            timeout = config.timeout

        if n_retries is None:
            n_retries = config.n_retries

        self.limit = limit
        self.timeout = timeout
        self.n_retries = n_retries

    @property
    def downloaded(self):
        return self._downloaded

    @downloaded.setter
    def downloaded(self, value):
        self._downloaded = value

        self.emit_event("downloaded_changed", value)

    def begin(self):
        raise NotImplementedError
