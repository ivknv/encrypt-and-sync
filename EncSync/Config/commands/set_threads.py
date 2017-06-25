#!/usr/bin/env python
# -*- coding: utf-8 -*-

def set_sync_threads(config, args):
    number = int(args[0])
    if number < 1:
        raise ValueError("Number of threads must be positive")

    config.sync_threads = number

def set_scan_threads(config, args):
    number = int(args[0])
    if number < 1:
        raise ValueError("Number of threads must be positive")

    config.scan_threads = number

def set_download_threads(config, args):
    number = int(args[0])
    if number < 1:
        raise ValueError("Number of threads must be positive")

    config.download_threads = number
