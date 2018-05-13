#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...encscript import Namespace
from . import commands

__all__ = ["ConsoleNamespace"]

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
        self["rmdup"]      = commands.RemoveDuplicatesCommand
