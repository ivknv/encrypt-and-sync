#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import setup, find_packages

requirements = ["s3m>=1.0.5", "pycryptodome", "portalocker"]

if os.environ.get("USE_FASTER_SCRIPTS", None):
    entry_points = {}

    if sys.platform.startswith("win"):
        scripts = ["bin/encsync.bat", "bin/encsync3.bat"]
    else:
        scripts = ["bin/encsync3", "bin/encsync"]
else:
    entry_points = {"console_scripts": ["encsync=EncSync.__main__:main"]}
    scripts = []

setup(name="EncSync",
      version="0.6.0",
      description="A file synchronization utility with client-side encryption support",
      author="Ivan Konovalov",
      packages=find_packages(exclude=["tests"]),
      install_requires=requirements,
      extras_require={"yandex.disk": ["yadisk>=1.2.5", "requests"],
                      "dropbox":     ["dropbox", "requests"],
                      "sftp":        ["pysftp", "paramiko"]},
      entry_points=entry_points,
      scripts=scripts)
