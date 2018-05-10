###############
Getting Started
###############

============
Installation
============

---------------------
Installing on Windows
---------------------

.. _here (32-bit): https://encrypt-and-sync.com/download/windows/eas-0.6.2-win32.zip
.. _here (64-bit): https://encrypt-and-sync.com/download/windows/eas-0.6.2-win64.zip

1. Download the portable zip archive from `here (64-bit)`_ or `here (32-bit)`_
2. Unpack it anywhere you want
3. The executables are in the :code:`bin` directory
4. You can add the bin directory to :code:`PATH` for convenience

------------------------
Installing on Arch Linux
------------------------

^^^^^^^^^^^^^^^^^^^
Installing from AUR
^^^^^^^^^^^^^^^^^^^

Install from AUR using yaourt:

.. code:: bash

   yaourt -S python-eas

^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Installing from the website
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Download the package from `here <https://encrypt-and-sync.com/download/python/python-eas-0.6.2-any.pkg.tar.xz>`_
2. Install it with pacman:

.. code:: bash

   sudo pacman -S python-eas-0.6.2-any.pkg.tar.xz

---------------------------
Installing on Debian/Ubuntu
---------------------------

.. _here (Debian): https://encrypt-and-sync.com/download/debian/python3-eas-0.6.2_all.deb
.. _here (Ubuntu): https://encrypt-and-sync.com/download/ubuntu/python3-eas-0.6.2_all.deb

1. Download the package from `here (Debian)`_ or `here (Ubuntu)`_
2. Install it with dpkg:

.. code:: bash

   sudo dpkg -i python3-eas-0.6.2_all.deb

---------------------------
Installing on other systems
---------------------------

^^^^^^^^^^^^^^^^^^^^
Installing from PyPI
^^^^^^^^^^^^^^^^^^^^

Install from PyPI using pip:

.. code:: bash

   pip install eas

^^^^^^^^^^^^^^^^^^^^^^^^
Install from the website
^^^^^^^^^^^^^^^^^^^^^^^^

1. Download the python wheel from `here <https://encrypt-and-sync.com/download/python/eas-0.6.2-py3-none-any.whl>`_
2. Install it with pip:

.. code:: bash

   pip install eas-0.6.2-py3-none-any.whl

=============
Configuration
=============

-------------------------
Interactive configuration
-------------------------

To interactively edit the configuration, run

.. code:: bash

   eas configure

Using the above command you can also change the master password and the encryption key.

It is recommended for you to take a look at :ref:`concepts`, as well as :code:`--help`:

.. code:: bash

   eas --help

--------------------
Manual configuration
--------------------

The configuration file is located at :code:`~/.eas/eas.conf`.

You can generate a sample configuration by running

.. code:: bash

   eas make-config ~/.eas/eas.conf

See :ref:`configuration`.
