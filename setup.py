#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import sys

requirements = ["requests", "PyCrypto"]

if sys.platform.startswith("win"):
    requirements.append("pyreadline")

setup(name="EncSync",
      version="0.1.4",
      description="Yandex.Disk encrypted sync tool",
      author="Ivan Konovalov",
      packages=find_packages(),
      install_requires=requirements,
      entry_points={"console_scripts": ["encsync=EncSync.__main__:main"]})
