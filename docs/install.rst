Installation
============

Install Options
---------------

When installing `bapsf_motion` there are three install options tailored
for end-user use and four options tailored for developer use.

.. table:: End-User Install Options
    :widths: auto

    +-------------------------+------------------------------------------------+
    | Option                  | Description                                    |
    +=========================+================================================+
    | ``bapsf_motion``        | Installs all dependencies, **EXCLUDING** GUI   |
    |                         | dependencies, to used the core functionality   |
    |                         | on 64-bit systems.                             |
    +-------------------------+------------------------------------------------+
    | ``bapsf_motion[gui]``   | Installs all dependencies, **INCLUDING** GUI   |
    |                         | dependencies, to used the core functionality   |
    |                         | on 64-bit systems.                             |
    +-------------------------+------------------------------------------------+
    | ``bapsf_motion[32bit]`` | Installs dependencies for 32-bit systems.      |
    |                         | This **EXCLUDES** GUI dependencies, since the  |
    |                         | GUI functionality ONLY works on 64-bit         |
    |                         | systems.                                       |
    +-------------------------+------------------------------------------------+

.. table:: Developer Install Options
    :widths: auto

    +--------------------------+-----------------------------------------------+
    | Option                   | Description                                   |
    +==========================+===============================================+
    | ``bapsf_motion[docs]``   | Installs dependencies on top of               |
    |                          | ``bapsf_motion[gui]`` for developing and      |
    |                          | building the package documentation.           |
    +--------------------------+-----------------------------------------------+
    | ``bapsf_motion[tests]``  | Installs dependencies on top of               |
    |                          | ``bapsf_motion[gui]`` for developing and      |
    |                          | running the package tests.                    |
    +--------------------------+-----------------------------------------------+
    | ``bapsf_motion[extras]`` | Installs dependencies on top of               |
    |                          | ``bapsf_motion[gui]`` for running package     |
    |                          | linters.                                      |
    +--------------------------+-----------------------------------------------+
    | ``bapsf_motion[dev]``    | Installs **ALL** package dependencies.        |
    +--------------------------+-----------------------------------------------+


Installing from ``pip``
-----------------------

The `bapsf_motion` package is registered with
`PyPI <https://pypi.org/project/bapsf_motion/>`__ and can be installed with
pip_ via

.. code-block:: bash

    pip install bapsf_motion

If you want to install pre-releases, then use the ``--pre`` flag

.. code-block:: bash

    pip install bapsf_motion --pre

For the most recent development version, `bapsf_motion` can be
installed from `GitHub <https://github.com/BaPSF/bapsf_motion>`__, see
additional details below.

Installing Directly from GitHub
-------------------------------

To install directly from GitHub, you need to have
`git <https://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`__
installed on your computer.  If you do not have ``git`` installed,
then see `Installing from a GitHub Clone or Download`_.

To install directly from the ``main`` branch invoke the following
command

.. code-block:: bash

    pip install git+https://github.com/BaPSF/bapsf_motion.git#egg=bapsf_motion

If an alternate branch ``BranchName`` is desired, then invoke

.. code-block:: bash

    pip install git+https://github.com/BaPSF/bapsf_motion.git@BranchName#egg=bapsf_motion

Installing from a GitHub Clone or Download
------------------------------------------

A copy of the `bapsf_motion` package can be obtained by
`cloning <https://help.github.com/articles/cloning-a-repository/>`_
or downloading from the GitHub repository.

Cloning the repository requires an installation of ``git`` on your
computer.  To clone the ``main`` branch, first, on your computer,
navigate to the directory you want the clone and do

.. code-block:: bash

    git clone https://github.com/BaPSF/bapsf_motion.git

To download a copy, go to the
`repository <https://github.com/BaPSF/bapsflib>`_, select the branch to
be downloaded, click the green button labeled :ibf:`Code`,
select :ibf:`Download ZIP`, save the zip file to the desired directory,
and unpack.

After getting a copy of the `bapsf_motion` package (via clone or
download), navigate to the main package directory, where the package
:file:`setup.py` file is located, and execute

.. code-block:: bash

    pip install .

Useful Installation Links
-------------------------

* bapsf_motion repository: https://github.com/BaPSF/bapsf_motion
* bapsf_motion on PyPI: https://pypi.org/project/bapsf_motion/
* pip documentation: https://pip.pypa.io/en/stable/
* git installation: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git
* cloning and downloading form GitHub: https://help.github.com/articles/cloning-a-repository/
