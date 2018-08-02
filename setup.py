#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os
import sys

from setuptools import setup, find_packages

requirements = ["s3m>=1.1.0", "pycryptodome", "portalocker"]

if sys.platform.startswith("win"):
    requirements.append("pypiwin32")
    requirements.append("eventlet")

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

if os.environ.get("USE_PYCRYPTODOMEX", None):
    requirements[requirements.index("pycryptodome")] = "pycryptodomex"

module_dir = os.path.dirname(__file__)

with codecs.open(os.path.join(module_dir, "README.rst"), encoding="utf8") as f:
    long_description = f.read()

setup(name="eas",
      version="0.7.2",
      description="Encrypt & Sync is a file synchronization utility with client-side encryption support",
      long_description=long_description,
      url="https://encryptandsync.com",
      project_urls={"Website":       "https://encryptandsync.com",
                    "Source code":   "https://github.com/ivknv/encrypt-and-sync",
                    "Documentation": "https://encryptandsync.com/docs",
                    "Bug tracker":   "https://github.com/ivknv/encrypt-and-sync/issues",
                    "Donate":        "https://paypal.me/encryptandsync"},
      author="Ivan Konovalov",
      author_email="ivknv0@gmail.com",
      license="GPLv3",
      packages=find_packages(exclude=["tests"]),
      install_requires=requirements,
      python_requires=">=3.5",
      extras_require={"yandex.disk": ["yadisk>=1.2.5", "requests"],
                      "dropbox":     ["dropbox", "requests"],
                      "sftp":        ["pysftp", "paramiko"]},
      entry_points=entry_points,
      scripts=scripts,
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: End Users/Desktop",
          "Intended Audience :: System Administrators",
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
          "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Operating System :: OS Independent",
          "Topic :: Internet",
          "Topic :: Utilities"],
      keywords="sync encryption dropbox yandex sftp")
