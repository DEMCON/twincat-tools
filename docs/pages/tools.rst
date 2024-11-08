#####
Tools
#####


.. _xml_sorter:

XML Sorter
==========

TwinCAT saves its project files somewhat arbitrarily, the order of elements is changed seemingly at random.
Use this XML sorter before committing your changes to fix the XML layout and keep your Git history more clean.

Usage
-----

Call with ``python -m tctools.xml_sort`` or ``tc_xml_sort``.

.. argparse::
   :module: tctools.xml_sort.__main__
   :func: get_parser
   :nodescription:

   --filter : @replace
      Target files only with these patterns

      Default: ['\*.tsproj', '\*.xti', '\*.plcproj']

.. Overwrite the --filter argument because the asterisks mess up the formatting

Notes
-----

* Nodes with the attribute ``xml:space="preserve"`` are not touched

Differences with Ruud's XmlSorter
---------------------------------

The precursor of this script is the XmlSorter made by Ruud, written in C#: https://github.com/DEMCON/XmlSorter

There are a couple of difference between this sorter and Ruud's:

* The root attribute `xmlns:xsi` cannot be sorted

  * This is because `lxml` does not show it as an attribute.

* This sorter will prefer self-closing tags where content is emtpy, instead of leaving them as they were.

  * This is a consequence of ``lxml``, it cannot identify self-closing tags upon reading.
  * The self-closing tags also do not have a trailing space before the final ``"/>"``.

* Unicode characters are written as ``#...;`` instead of literals.

  * Something ``lxml`` just seems to do.

**None** of these appear problematic for TwinCAT.
Projects can be opened and built again as expected, and when saved again the file will be as TwinCAT likes it.


.. _auto_formatter:

Auto Formatter
==============

Use this to make consistent use of whitespace.
Visual Studio with PLC doesn't do a lot of the things that other IDEs do, like removing trailing whitespace and making
consistent usage of spaces / tabs.
This tool is meant to supplement this.

Specify your preferences with an `.editorconfig` `file <https://editorconfig.org/>`_, as you would for other projects.
An example:

.. code-block::

   [*.TcPOU]
   indent_style = space
   indent_size = 4

Usage
-----

Call with ``python -m tctools.format`` or ``tc_format``.

.. argparse::
   :module: tctools.format.__main__
   :func: get_parser
   :nodescription:

   --filter : @replace
      Target files only with these patterns

      Default: ['\*.tsproj', '\*.xti', '\*.plcproj']

.. Overwrite the --filter argument because the asterisks mess up the formatting

Valid options
-------------

The following universal ``.editorconfig`` fields are considered:

* ``indent_style``

  * If style is set to space, any tab character will be replaced by ``tab_width`` number of spaces
  * If style is set to tab, any ``tab_width``-number of spaces will be replaced by a tab

* ``trim_trailing_whitespace``

  * If true, whitespace at the end of lines is removed

* ``insert_final_newline``

  * If true, every code block must end with a newline

And The following unofficial (custom) ``.editorconfig`` fields are used:

* ``twincat_align_variables``

  * If true, variables in declarations are aligned together
* ``twincat_parentheses_conditionals``

  * If true, parentheses are enforced inside if-statements (``IF (condition = 1) THEN...``)
  * If false, parentheses inside if-statements are removed (``IF condition = 1 THEN...``)

When a config property is not set, the formatter will typically take no action.
For example, not specifying ``indent_style`` (or using ``unset``) will result in no whitespace conversions at all.


.. _git_info:

Git Info
========

Use to insert Git version into source file based on a template, to make it available for compilation.

Create a template file (e.g. ``.TcGVL.template``), with ``{{...}}`` tags as placeholders for the version info.
Then run the info tool (preferably as part of your build) to have it create a new file next to it.

Usage
-----

Call with ``python -m tctools.git_info`` or ``tc_git_info``.

.. argparse::
   :module: tctools.git_info.__main__
   :func: get_parser
   :nodescription:

Placeholders
------------

* ``GIT_HASH``: Hash of the last commit (full 40 hex characters)
* ``GIT_HASH_SHORT``: First 8 characters of the last commit hash
* ``GIT_DATE``: Datetime of the last commit
* ``GIT_TAG``: Most recent tag of this branch
* ``GIT_BRANCH``: Currently checked out branch
* ``GIT_DESCRIPTION``: Result of ``git describe --tags --always`` (e.g. `v0.0.3a-4-g51994a8`)
* ``GIT_DESCRIPTION_DIRTY``: Result of ``git describe --tags --always --dirty`` (e.g. `v0.0.3a-4-g51994a8-dirty`)

Notes
-----

* Requires Git, likely required to be added to ``PATH``.


.. _make_release:

Release Maker
=============

Use to produce a release archive of compiled PLC code, optionally together with compiled HMI application.

Usage
-----

Call with ``python -m tctools.make_release`` or ``tc_make_release``.

.. argparse::
   :module: tctools.make_release.__main__
   :func: get_parser
   :nodescription:
