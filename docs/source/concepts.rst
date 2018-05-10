.. _concepts:

################
Concepts & Usage
################

======
Folder
======

A folder refers to a directory in a certain storage.
Folder path is specified like this: :code:`<storage-name>:///path/to/the/folder`.
If :code:`<storage-name>` is empty, the path will be considered local.

------------------
Supported storages
------------------

+--------------+--------------------------------------------+
| Storage name | Path example                               |
+==============+============================================+
| Local        | /local/path or local:///local/path         |
+--------------+--------------------------------------------+
| Yandex.Disk  | disk://remote/path or yadisk://remote/path |
+--------------+--------------------------------------------+
| Dropbox      | dropbox:///remote/path                     |
+--------------+--------------------------------------------+
| SFTP         | sftp://user@host:22/some/path              |
+--------------+--------------------------------------------+                        

Every folder must also have a name.
Folder names must only contain the following characters:

* Letters, including unicode
* Digits
* _ (underscore), - (minus), + (plus) and . (dot).

Folders can be specified manually in the configuration file or interactively using the configure command.

==========
Encryption
==========

Encrypt & Sync uses AES encryption to encrypt file content and filenames.
The encryption key is stored in a separate file, encrypted with the master password.

.. note::

   If you want to change the encryption key, you'll have to re-encrypt all your existing folders that use the current key. This doesn't apply to changing the master password.

-------------------
Filename encryption
-------------------

After the filenames are encrypted they are essentially just a bunch of random bytes, so they need to be encoded.

There are several different filename encodings for that but it's very likely that you'll never need to use anything other than base32.
The only possible reason for that is if you have very long filenames (over 128 characters).
In that case you can take a look at all the available encodings and pick the one that suits your needs.

.. note::

   If you have an existing folder that uses some filename encoding and you
   want to use a different one, you'll have to re-encrypt the entire folder.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Supported filename encodings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

+-------------------+----------------+----------+-------------+
| Filename encoding | Case-sensitive | Standard | Max. length |
+===================+================+==========+=============+
| base64 (default)  | |yes|          | |yes|    | 160         |
+-------------------+----------------+----------+-------------+
| base41            | |no|           | |no|     | 144         |
+-------------------+----------------+----------+-------------+
| base32            | |no|           | |yes|    | 128         |
+-------------------+----------------+----------+-------------+

.. |yes| unicode:: U+2713
.. |no| unicode:: U+2717

.. note::

   The table assumes that the maximum unencrypted filename length is 255 bytes, which varies across different systems and cloud services.

============
Synchronizer
============

The main component that does the actual synchronization of files. It divides the work into targets, which later get divided into tasks. Sync targets require the source and the destination folders to be specified.

In order to synchronize folders, you can run:

.. code:: bash

   eas sync <source-folder> <destination-folder>

See :code:`eas sync --help` for additional information.

=======
Scanner
=======

Before you can sync the folders they need to be scanned first. Scanner is the component responsible for this. It's goal is to obtain the list of files a folder has. Synchronizer does this automatically, unless it's specifically told not to do that.

In order to manually scan a folder, you can run:

.. code:: bash

   eas scan <folder1> <folder2> ...

See :code:`eas scan --help` for additional information.

==========
Downloader
==========

In case you want to download some files (or even whole folders), there's a downloader.

In order to download something, run:

.. code:: bash

   eas download <source-path> <destination-path>

See :code:`eas download --help` for additional information.

=================
Duplicate remover
=================

Sometimes, if the synchronizer dies in the middle of uploading a file, it can produce file duplicates next time, thinking that the file wasn't actually uploaded. It's very rare and it only happens to encrypted folders. Duplicates are not dangerous, they just waste space.

The existence of duplicates is a consequence of using randomly-generated IVs (initialization vectors) for AES encryption of filenames. Because of this, you can have two files (or directories) with different encrypted filenames, but when you decrypt them — you get the same filename.

Fortunately, it's not hard to identify and remove them (not that you normally have to). Duplicates are identified by the scanner and removed by the duplicate remover. This is normally done automatically as a separate stage of synchronization.

To manually remove duplicates, run:

.. code:: bash

   eas remove-duplicates <path1> <path2> ...

See :code:`eas remove-duplicates --help` for additional information.
