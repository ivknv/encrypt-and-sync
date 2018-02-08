# EncSync
EncSync is a command line file synchronizer with encryption support (including filename encryption).

Supported storages at the moment (there will be more in the future):
1. Local
2. Yandex.Disk

It can sync files in both directions, as well as download them.

## Features
1. Encryption (optional)
2. Synchronization in both directions
3. Downloader
4. Multithreading
5. Auto-retries for failing requsts

## Installation
EncSync requires Python >= 3.5.

To install, run
```sh
python setup.py install
```

## Configuration
### Setting the master password and the encryption key
In order to set the master password, run
```sh
encsync set-master-password
```

To set the encryption key, run
```sh
encsync set-key
```

### The configuration file
The configuration file is located at `~/.encsync/encsync.conf`.
You can generate a sample configuration by running
```sh
encsync make-config ~/.encsync/encsync.conf
```
