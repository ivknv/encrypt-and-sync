#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..EncScript import Namespace
from . import commands, blocks

class ConfigNamespace(Namespace):
    def __init__(self):
        Namespace.__init__(self)

        self["sync-threads"] = commands.SyncThreadsCommand
        self["scan-threads"] = commands.ScanThreadsCommand
        self["upload-limit"] = commands.UploadLimitCommand
        self["download-limit"] = commands.DownloadLimitCommand
        self["download-threads"] = commands.DownloadThreadsCommand

        self["targets"] = blocks.TargetsBlock
        self["include"] = blocks.IncludeBlock
        self["exclude"] = blocks.ExcludeBlock
        self["encrypted-dirs"] = blocks.EncryptedDirsBlock
