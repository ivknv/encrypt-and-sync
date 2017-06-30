#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import show_error

DEFAULT_CONFIG = """\
# Number of threads for synchronizer, scanner and downloader respectively
sync-threads 2
scan-threads 2
download-threads 2

# Upload/Download speed limits
# inf means infinity or no speed limit
# 8192 means 8912 Bytes
# 1.2m means 1.2 MiB
# 500k means 500 KiB
upload-limit inf
download-limit inf

# List of targets to sync
targets {
    # preferred-target-name /path/to/local/dir /path/to/remote/dir
    # OR
    # /path/to/local/dir /path/to/remote/dir
}

# List of remote directories that are known to be encrypted but not listed in targets
# This is required by console commands like 'ls', 'cat', etc.
encrypted-dirs {
    # /path/to/remote/dir1
    # /path/to/remote/dir2
}

# List of patterns to exclude when performing local scan
# The synchronizer will think they don't exist
# You can have multiple include/exclude blocks
# They will be interpreted in specified order
exclude {
    # /path/to/local/*.txt
    # /path/to/local/dir2
}

# This can cancel out any previous exclude blocks, works the same way
include {
    # /path/to/local/*.txt
    # /path/to/local/dir2
}"""

def make_config(env, path):
    try:
        with open(path, "w") as f:
            f.write(DEFAULT_CONFIG)
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % path)
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % path)
        return 1

    return 0
