#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import show_error

__all__ = ["generate_config"]

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

# Request timeouts, inf to disable
connect-timeout 10
read-timeout 15

# Number of request retries
n-retries 10

# Upload timeouts, inf to disable
upload-connect-timeout 10
upload-read-timeout 60

# Specify folders
# Folder name can contain digits, characters of english alphabet, '+', '-', '_' and '.'
# A path that starts with local:// is a local one
# A path that starts with disk:// or yadisk:// is a Yandex.Disk path
folders {
#    folder1 /path/to/local/folder {}
#    folder2 disk://path/to/remote/folder {
#        encrypted true
#        filename-encoding base64 # optional
#        avoid-rescan false # optional
#    }
}

# Default targets to sync (when given -a or --all)
targets {
#    folder1 -> folder2
#    folder2 -> folder1
}

# List of patterns to exclude when performing scan
# The synchronizer will think they don't exist
# You can have multiple include/exclude blocks
# They will be interpreted in specified order
exclude {
    # /path/to/local/*.txt
    # /path/to/local/dir2/
    # yadisk:///path/to/yadisk/dir/
    # dropbox:///path/to/dropbox/dir/
}

# This can cancel out any previous exclude blocks, works the same way
include {
    # /path/to/local/*.txt
    # /path/to/local/dir2/
    # yadisk:///path/to/yadisk/dir/
    # dropbox:///path/to/dropbox/dir/
}"""

def generate_config(env, path):
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
