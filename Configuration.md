# Configuration
## Syntax
The syntax is mostly similar to BASH, although, there are no variables and nested commands.

## Commands
`sync-threads <non-negative-integer>` - sets the number of threads used for synchronization.

`scan-threads <non-negative-integer>` - sets the number of threads used for scanning.

`download-threads <non-negative-integer>` - sets the number of threads used for downloading.

`upload-limit <upload-speed>` - sets the maximum file upload speed. `1.5m` means 1.5 MiB per second, `300k` means 300 KiB, etc.

`download-limit <upload-speed>` - sets the maximum file download speed. `1.5m` means 1.5 MiB per second, `300k` means 300 KiB, etc.

`n-retries <non-negative-integer>` - sets the maximum number of retries for failing requests.

`connect-timeout <positive-number>` - sets the connect timeout in seconds.

`read-timeout <positive-number>` - sets the read timeout in seconds.

## Blocks
### `exclude`
This block can be used to exclude files from the synchronization.
This can also speed up the scan.

Usage:
```sh
exclude {
    /path/to/local/dir/
    /path/to/local/file
    disk://path/to/remote/file
    *.py[co] # Globbing is supported too
}
```

### `include`
Does the opposite of the `exclude` block.

Usage:
```sh
include {
    /path/to/local/dir/
    /path/to/local/file
    disk://path/to/remote/file
    *.py[co] # Globbing is supported too
}
```

### `targets`
This block specifies the default targets to sync when the synchronizer receives `-a` (`--all`) argument.

Usage:
```sh
targets {
    python-local -> python-yadisk # From python-local to python-yadisk
    c++-local <- c++-yadisk # From c++-yadisk to c++-local
    folder1-local -> folder2-yadisk
    folder2-local => folder1-yadisk
    folder3-local folder3-yadisk
}
```

### `folders`
This block is used to specify folders.
Folder name must only contain letters, digits, '\_', '-', '+' and '.'.

Usage:
```sh
folders {
    python-local ~/Python {}
    python-yadisk disk://Python {
        encrypted true
        avoid-rescan true # Makes synchronizer avoid scanning the folder, unless it's empty in the database
        filename-encoding base64 # base64 is the default filename encoding
    }

    remote-only-folder disk://SomeFolder {
        encrypted true
    }
}
```

`encrypted [true | false]` - enable/disable folder encryption.

`avoid-rescan [true | false]` - makes synchronizer scan the folder only if it's empty in the database.

`filename-encoding [base64 | base41]` - sets encoding used for encrypted filenames.
