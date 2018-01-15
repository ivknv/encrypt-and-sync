#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import setup, find_packages

requirements = ["s3m>=1.0.3", "requests", "pycryptodome", "yadisk>=1.2.1"]

readline_pkg = "readline"

if sys.platform.startswith("win"):
    readline_pkg = "pyreadline"

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
      version="0.2.0",
      description="Yandex.Disk encrypted sync tool",
      author="Ivan Konovalov",
      packages=find_packages(exclude=["tests"]),
      install_requires=requirements,
      extras_require={"readline": [readline_pkg]},
      entry_points=entry_points,
      scripts=scripts)
