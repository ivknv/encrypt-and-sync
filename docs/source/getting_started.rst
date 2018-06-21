###############
Getting Started
###############

============
Installation
============

---------------------
Installing on Windows
---------------------

.. _here (32-bit): https://encrypt-and-sync.com/download/windows/eas-0.7.0-win32.zip
.. _here (64-bit): https://encrypt-and-sync.com/download/windows/eas-0.7.0-win64.zip

1. Download the portable zip archive from `here (64-bit)`_ or `here (32-bit)`_
2. Unpack it anywhere you want
3. The executables are in the :code:`bin` directory
4. You can add the bin directory to :code:`PATH` for convenience

------------------------
Installing on Arch Linux
------------------------

Install the package from AUR using aurman:

.. code:: bash

   aurman -S python-eas

---------------------------
Installing on Ubuntu
---------------------------

1. Add the PPA:

.. code:: bash

   sudo add-apt-repository ppa:ivknv/encrypt-and-sync

2. Install the package with apt-get:

.. code:: bash

   sudo apt-get update
   sudo apt-get install python3-eas

---------------------------
Installing on other systems
---------------------------

^^^^^^^^^^^^^^^^^^^^
Installing from PyPI
^^^^^^^^^^^^^^^^^^^^

Install from PyPI using pip:

.. code:: bash

   pip install eas

^^^^^^^^^^^^^^^^^^^^^^^^^^^
Installing from the website
^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Download the python wheel from `here <https://encrypt-and-sync.com/download/python/eas-0.7.0-py3-none-any.whl>`_
2. Install it with pip:

.. code:: bash

   pip install eas-0.7.0-py3-none-any.whl

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
