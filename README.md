# EncSync
EncSync is a command line file synchronizer with encryption support (including filename encryption).

Supported storages at the moment (there will be more in the future):
1. Local
2. Yandex.Disk

It can sync files in both directions, as well as download them.

## Features
1. Encryption support, including filename encryption
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

For additional information, see `Configuration.md`.

## Concepts
### Folder
A folder refers to a directory in a certain storage.
A storage can be either local or Yandex.Disk at the moment.
Folder path is specified like this: `<storage-name>:///path/to/the/folder`,
where `<storage-name>` can be either 'local' or 'yadisk'.
In folder paths you can also use 'disk' as a synonym for 'yadisk'.
If `<storage-name>` is empty, the path will be considered local.

Every folder must also have a name.
One folder name can have several paths on different storages associated with it.
The specific path can be specified like this: `<folder-name>:<storage-name>`.

The folders can be specified in the configuration file.

### Encryption
EncSync uses AES encryption to encrypt file content and filenames.
After the filenames are encrypted they are just a bunch of unreadable bytes, so they need to be encoded.
There are 2 filename encodings supported at the moment: `base64` and `base41`.

Base64 is case-sensitive sensitive.
Base41 is case-insensitive, but at the cost of producing longer filenames.

### Synchronizer
The main component that does the actual synchronization of files.
It divides the work into targets, which later get divided into tasks.
Sync targets require the source folder and the destination folder to be specified.

In order to synchronize folders, you can run:
```sh
encsync sync <source-folder>:<source-storage> <destination-folder>:<destination-storage>
```

See `encsync sync --help` for additional information.

### Scanner
Before you can sync the folders they need to be scanned first.
Scanner is the component responsible for this.
It's goal is to obtain the list of files a folder has.
Synchronizer does this automatically, unless it's specifically told not to do that.

In order to manually scan a folder, you can run:
```sh
encsync scan <folder1>:<storage1> <folder2>:<storage2> ...
```

See `encsync scan --help` for additional information.

### Downloader
In case you want to download some files (or even whole folders), there's a downloader.

In order to download something, run:
```sh
encsync download <source-path> <destination-path>
```

See `encsync download --help` for additional information.

### Duplicate remover
Sometimes, if the synchronizer dies in the middle of uploading a file,
it can produce file duplicates next time, thinking that the file wasn't actually uploaded.
It only happens if it uploads to an encrypted folder.
This is a consequence of using randomly-generated IVs (initialization vectors) for AES encryption of filenames.
In the end you can have two files (or directories) with different encrypted filenames
but when you decrypt them, you get the same filename.

Fortunately, it's not hard to identify and remove them.
Duplicates are identified by the scanner and removed by the duplicate remover.

To manually remove duplicates, run:
```sh
encsync remove-duplicates <path1> <path2> ...
```

See `encsync remove-duplicates --help` for additional information.
