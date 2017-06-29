#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(name="EncSync",
      version="0.1.1",
      description="Yandex.Disk encrypted sync tool",
      author="Ivan Konovalov",
      packages=find_packages(),
      install_requires=["requests", "PyCrypto", "readline"],
      entry_points={"console_scripts": ["encsync=EncSync.__main__:main"]})
