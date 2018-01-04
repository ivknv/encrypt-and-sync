#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...EncScript import Namespace
from . import commands

class ConsoleNamespace(Namespace):
    def __init__(self, parent=None):
        Namespace.__init__(self, parent)

        self["ls"]         = commands.LsCommand
        self["cd"]         = commands.CdCommand
        self["cat"]        = commands.CatCommand
        self["exit"]       = commands.ExitCommand
        self["quit"]       = commands.ExitCommand
        self["echo"]       = commands.EchoCommand
        self["download"]   = commands.DownloadCommand
        self["scan"]       = commands.ScanCommand
        self["sync"]       = commands.SyncCommand
        self["diffs"]      = commands.DiffsCommand
        self["duplicates"] = commands.DuplicatesCommand
        self["src-scan"]   = commands.SrcScanCommand
        self["dst-scan"]   = commands.DstScanCommand
        self["rmdup"]      = commands.RemoveDuplicatesCommand
