######
Config
######

The tools mostly share the same configuration methods.
The following priority is given to options:

#. Command line arguments
#. Config file ``tctools.toml``
#. General config file ``pyproject.toml``
#. Extra config files (e.g. ``.editorconfig``)

In case options are available in multiple files, only the one with the highest priority is considered.
I.e. options are not merged across levels: having entries in both ``tctools.toml`` and in ``pyproject.toml`` makes the ones in ``pyproject.toml`` be ignored.

The exception is for the :ref:`auto_formatter`, where the ``.editorconfig`` file(s) are still always considered.

Recommended
===========

It is recommended to put all customization in the ``pyproject.toml`` file.
You should already have such a file in order to require this package for your project (ideally with an exact version pinned), so then it's sensible to put other options below it as well.

Config File
===========

``tctools.toml`` and ``pyproject.toml`` both have the same syntax.
Add options under a section:

.. code-block:: toml

   # ...

   [tctools.tool]
   option = "value"
   # ...

Substitute ``tool`` for either ``format``, ``xml_sort``, ``git_info`` or ``make_release``, and replace ``option`` and ``"value"`` for meaningful entries.

See pages about each tool for available options.
The options are named the same as the command line arguments, except without any leading dashes and with any other dashes (``-``) replaced by underscores (``_``).
