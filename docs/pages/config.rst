######
Config
######

The tools mostly share the same configuration methods.
The following priority is given to options:

#. Command line arguments
#. Sections of config file ``tctools.toml``
#. Sections of general config file ``pyproject.toml``
#. Extra config files (e.g. ``.editorconfig``)

In case options are available in multiple files, only the section with the highest priority is considered.
I.e. options are not merged down to the smallest level.

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

Substitute ``tool`` for a specific tool and ``option`` and ``"value"`` for meaningful entries.

See pages about each tool for available options.
