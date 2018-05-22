.. _configuration:

#############
Configuration
#############

======
Syntax
======

The syntax is mostly similar to BASH, although, there are no variables and nested commands.

========
Commands
========

------------
sync-threads
------------

Sets the number of threads used for synchronization.

Usage:

.. code:: bash

   sync-threads <positive-integer>

------------
scan-threads
------------

Sets the number of threads used for scanning.

Usage:

.. code:: bash

   scan-threads <positive-integer>

----------------
download-threads
----------------

Sets the number of threads used for downloading.

Usage:

.. code:: bash

   download-threads <positive-integer>

------------
upload-limit
------------

Sets the maximum file upload speed. :code:`1.5m` means 1.5 MiB per second, :code:`300k` means 300 KiB, etc.

Usage:

.. code:: bash

   upload-limit <upload-speed>

   # Examples:
   upload-limit 1.3m # 1.3 MiB
   upload-limit 500k # 500 KiB
   upload-limit inf # no limit (infinity)

--------------
download-limit
--------------

Sets the maximum file download speed. :code:`1.5m` means 1.5 MiB per second, :code:`300k` means 300 KiB, etc.

Usage:

.. code:: bash

   download-limit <download-speed>

   # Examples:
   download-limit 1.5m # 1.5 MiB
   download-limit 500k # 500 KiB
   download-limit inf # no limit (infinity)

---------
n-retries
---------

Sets the maximum number of retries for failing requests.

Usage:

.. code:: bash

   n-retries <non-negative-integer>

   # Examples:
   n-retries 0 # disables retries
   n-retries 10
   n-retries 7

---------------
connect-timeout
---------------

Sets the connect timeout in seconds.

Usage:

.. code:: bash

   connect-timeout <positive-number>

   # Examples:
   connect-timeout 20
   connect-timeout 30

------------
read-timeout
------------

Sets the read timeout in seconds.

Usage:

.. code:: bash

   read-timeout <positive-number>

   # Examples:
   read-timeout 15
   read-timeout 25

-----------------------
scan-ignore-unreachable
-----------------------

Makes the scanner ignore unreachable files (e.g. encoding errors, denied permission, etc.).
:code:`false` is the default value.

Usage:

.. code:: bash

   scan-ignore-unreachable [true | false]

--------
temp-dir
--------

Sets the temporary directory to be used instead of the default (:code:`-`).

Usage:

.. code:: bash

   temp-dir [<directory> | -]

   # Examples:
   temp-dir ~/my-temp-dir
   temp-dir - # use the default directory

------------------------
temp-encrypt-buffer-size
------------------------

Sets the size for an in-memory buffer that is used for storing temporary files.

Usage:

.. code:: bash

   temp-encrypt-buffer-size <size>

   # Examples:
   temp-encrypt-buffer-size 50m # 50 MiB
   temp-encrypt-buffer-size 120m # 120 MiB
   temp-encrypt-buffer-size 0 # disables the buffer

======
Blocks
======

-------
exclude
-------

This block can be used to exclude files from the synchronization.
This can also speed up the scan.

Usage:

.. code:: bash

   exclude {
       /path/to/local/dir/
       /path/to/local/file
       disk://path/to/remote/file
       dropbox://another/remote/path/
       *.py[co] # Globbing is supported too
       disk://*.py[co]
   }

-------
include
-------

Does the opposite of the exclude block.

Usage:

.. code:: bash

   include {
       /path/to/local/dir/
       /path/to/local/file
       disk://path/to/remote/file
       dropbox://another/remote/path/
       *.py[co] # Globbing is supported too
       disk://*.py[co]
   }

-------
targets
-------

This block specifies the default targets to sync when the synchronizer receives :code:`-a` (:code:`--all`) argument.

Usage:

.. code:: bash

   targets {
       python-local -> python-yadisk # From python-local to python-yadisk
       c++-local <- c++-yadisk # From c++-yadisk to c++-local
       folder1-local -> folder2-yadisk
       folder2-local => folder1-yadisk
       folder3-local folder3-yadisk
   }

-------
folders
-------

This block is used to specify folders.
Folder name must only contain letters, digits, :code:`\_`, :code:`-`, :code:`+` and :code:`.`.

Usage:

.. code:: bash

   folders {
       <folder-name> <folder-path> {
           encrypted [true | false] # Enable/disable folder encryption, (false by default)
           avoid-rescan [true | false] # If true, makes the synchronizer avoid rescanning the folder, unless it's empty in the database
           filename-encoding [base64 | base41 | base32] # Filename encoding to use for encrypted filenames (base64 by default)
       }

       <folder-name> <folder-path> {}

       ...
   }

   # Examples:
   folders {
       python-local ~/Python {}

       python-yadisk disk://Python {
           encrypted true
           avoid-rescan true
           filename-encoding base64
       }

       remote-only-folder disk://SomeFolder {
           encrypted true
       }

       some-other-folder dropbox:///some/other/folder {
           encrypted true
           filename-encoding base32
       }
   }
