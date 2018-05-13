# -*- coding: utf-8 -*-

import io
import os
import shutil
import subprocess
import tempfile

__all__ = ["Pager"]

class Pager(object):
    """
        Pages output to the screen using less or more if either of them is available.

        :ivar mode: `str`, `self.stdin` mode
        :ivar stdin: file-like, file to be paged
        :ivar command: `str`, command used as an actual pager

        The text should be provided through `self.stdin.write`.

        :param pagers: list of `str`, (ordered) list of commands to use as pagers (if available)
        :param mode: `str`, `self.stdin` mode
    """

    def __init__(self, pagers=("less", "more"), mode="w+"):
        self.mode = mode
        self.command = None

        for name in pagers:
            self.command = shutil.which(name)

            if self.command is not None:
                break

        if self.command is not None:
            self.command = os.path.abspath(self.command)
            self.stdin = tempfile.TemporaryFile(mode)
        elif "b" in mode:
            self.stdin = io.BytesIO()
        else:
            self.stdin = io.StringIO()

    def run(self):
        """Page the text stored in `self.stdin`"""

        self.stdin.flush()
        self.stdin.seek(0)

        if self.command is not None:
            return subprocess.run([self.command], stdin=self.stdin)

        if "b" not in self.mode:
            for line in self.stdin:
                print(line, end="")
        else:
            for line in self.stdin:
                print(line.decode("utf8"), end="")
