#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import setup, find_packages

requirements = ["s3m>=1.0.5", "pycryptodome", "portalocker"]

if sys.platform.startswith("win"):
    requirements.append("pypiwin32")

if os.environ.get("USE_FASTER_SCRIPTS", None):
    entry_points = {}

    if sys.platform.startswith("win"):
        scripts = ["bin/eas.bat", "bin/eas3.bat"]
    else:
        scripts = ["bin/eas3", "bin/eas"]
else:
    entry_points = {"console_scripts": ["eas=eas.__main__:main",
                                        "encrypt-and-sync=eas.__main__:main"]}
    scripts = []

setup(name="eas",
      version="0.6.3",
      description="A file synchronization utility with client-side encryption support",
      author="Ivan Konovalov",
      license="GPLv3",
      packages=find_packages(exclude=["tests"]),
      install_requires=requirements,
      extras_require={"yandex.disk": ["yadisk>=1.2.5", "requests"],
                      "dropbox":     ["dropbox", "requests"],
                      "sftp":        ["pysftp", "paramiko"]},
      entry_points=entry_points,
      scripts=scripts)
