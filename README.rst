MOPUp
=====

|PyPI| |Status| |Python Version| |License|

|Read the Docs| |Tests| |Codecov|

|pre-commit| |Black|

.. |PyPI| image:: https://img.shields.io/pypi/v/MOPUp.svg
   :target: https://pypi.org/project/MOPUp/
   :alt: PyPI
.. |Status| image:: https://img.shields.io/pypi/status/MOPUp.svg
   :target: https://pypi.org/project/MOPUp/
   :alt: Status
.. |Python Version| image:: https://img.shields.io/pypi/pyversions/MOPUp
   :target: https://pypi.org/project/MOPUp
   :alt: Python Version
.. |License| image:: https://img.shields.io/pypi/l/MOPUp
   :target: https://opensource.org/licenses/MIT
   :alt: License
.. |Read the Docs| image:: https://img.shields.io/readthedocs/MOPUp/latest.svg?label=Read%20the%20Docs
   :target: https://MOPUp.readthedocs.io/
   :alt: Read the documentation at https://MOPUp.readthedocs.io/
.. |Tests| image:: https://github.com/glyph/MOPUp/workflows/Tests/badge.svg
   :target: https://github.com/glyph/MOPUp/actions?workflow=Tests
   :alt: Tests
.. |Codecov| image:: https://codecov.io/gh/glyph/MOPUp/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/glyph/MOPUp
   :alt: Codecov
.. |pre-commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
.. |Black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Black


Features
--------

MOPUp is the mac\ **O**\ S **P**\ ython.org **Updater**.

If you prefer to use the binary installers from python.org, it's easy to forget
to update them.  This is a program that does that; it updates them.  Just ``pip
install mopup`` into a virtualenv using the Python you are using, run ``mopup``
and provide your password when required.

Normally, it does this using a CLI in the background, but if you'd prefer, you
can run it with ``--interactive`` for it to launch the usual macOS GUI
Installer app.

Installation
------------

You can install *MOPUp* via pip_ from PyPI_:

.. code:: console

   $ pip install mopup


Usage
-----

Please see the `Command-line Reference <Usage_>`_ for details.


Contributing
------------

Contributions are very welcome.
To learn more, see the `Contributor Guide`_.


License
-------

Distributed under the terms of the `MIT license`_,
*MOPUp* is free and open source software.


Issues
------

If you encounter any problems,
please `file an issue`_ along with a detailed description.


Credits
-------

This project was generated from `@cjolowicz`_'s `Hypermodern Python Cookiecutter`_ template.

.. _@cjolowicz: https://github.com/cjolowicz
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _MIT license: https://opensource.org/licenses/MIT
.. _PyPI: https://pypi.org/
.. _Hypermodern Python Cookiecutter: https://github.com/cjolowicz/cookiecutter-hypermodern-python
.. _file an issue: https://github.com/glyph/MOPUp/issues
.. _pip: https://pip.pypa.io/
.. github-only
.. _Contributor Guide: CONTRIBUTING.rst
.. _Usage: https://MOPUp.readthedocs.io/en/latest/usage.html
