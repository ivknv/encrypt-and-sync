#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import sys

requirements = ["requests", "pycryptodome"]

readline_pkg = "readline"

if sys.platform.startswith("win"):
    readline_pkg = "pyreadline"

setup(name="EncSync",
      version="0.1.9",
      description="Yandex.Disk encrypted sync tool",
      author="Ivan Konovalov",
      packages=find_packages(),
      install_requires=requirements,
      extras_require={"readline": [readline_pkg]},
      entry_points={"console_scripts": ["encsync=EncSync.__main__:main"]})
