Usage
=====

Updating Python
---------------

Update your currently running Python version to its latest patch
release, also known as a micro release (for example from 3.13.2
to 3.13.7)::

    mopup update

Upgrade your currently running Python to a newer minor release
(for example from 3.13 to 3.14)::

    mopup update --minor=true

Update Python using the GUI installer::

    mopup update --interactive=true

Check for updates without installing (dry run)::

    mopup update --dry-run=true

Uninstalling Python
-------------------

Uninstalling with MOPUp removes all files and directories installed by
a specific Python.org installer. It will also remove any Python packages
installed within that Python version's ``site-packages`` directory.

However, it will refuse to uninstall if it detects extra files or
directories within that installation that were not listed by the
installer's manifest or any installed Python package's ``.dist-info``.

Uninstall a specific Python version::

    mopup uninstall 3.14

Preview what would be uninstalled without actually removing::

    mopup uninstall 3.14 --dry-run=true

Force uninstall even if extra files are present::

    mopup uninstall 3.14 --force=true

Command Reference
-----------------

.. click:: mopup.__main__:main
   :prog: mopup
   :nested: full
