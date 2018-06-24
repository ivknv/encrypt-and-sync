# -*- coding: utf-8 -*-

from ..task import Task

__all__ = ["UploadTask"]

class UploadTask(Task):
    """
        Events: uploaded_changed
    """

    def __init__(self, config, in_file, limit=None, timeout=None, n_retries=None):
        Task.__init__(self)

        self.config = config
        self.in_file = in_file
        self._uploaded = 0

        if limit is None:
            limit = config.upload_limit

        if timeout is None:
            timeout = config.upload_timeout

        if n_retries is None:
            n_retries = config.n_retries

        self.limit = limit
        self.timeout = timeout
        self.n_retries = n_retries

    @property
    def uploaded(self):
        return self._uploaded

    @uploaded.setter
    def uploaded(self, value):
        self._uploaded = value

        self.emit_event("uploaded_changed", value)

    def complete(self):
        raise NotImplementedError
