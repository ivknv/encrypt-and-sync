#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..encscript import Namespace
from . import commands, blocks

__all__ = ["ConfigNamespace"]

class ConfigNamespace(Namespace):
    def __init__(self):
        Namespace.__init__(self)

        self["sync-threads"] = commands.SyncThreadsCommand
        self["scan-threads"] = commands.ScanThreadsCommand
        self["upload-limit"] = commands.UploadLimitCommand
        self["download-limit"] = commands.DownloadLimitCommand
        self["temp-encrypt-buffer-limit"] = commands.TempEncryptBufferLimitCommand
        self["download-threads"] = commands.DownloadThreadsCommand
        self["connect-timeout"] = commands.ConnectTimeoutCommand
        self["read-timeout"] = commands.ReadTimeoutCommand
        self["upload-connect-timeout"] = commands.UploadConnectTimeoutCommand
        self["upload-read-timeout"] = commands.UploadReadTimeoutCommand
        self["n-retries"] = commands.NRetriesCommand
        self["scan-ignore-unreachable"] = commands.ScanIgnoreUnreachableCommand
        self["temp-dir"] = commands.TempDirCommand

        self["folders"] = blocks.FoldersBlock
        self["targets"] = blocks.TargetsBlock
        self["include"] = blocks.IncludeBlock
        self["exclude"] = blocks.ExcludeBlock
