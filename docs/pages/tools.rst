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

.. list-table::
   :widths: 25 50 25
   :header-rows: 1

   * - Placeholder
     - Description
     - Example
   * - GIT_HASH
     - Full hash of the last commit
     - ``4cc498b3c37375d8d9138fdab553ced012cafc7a``
   * - GIT_HASH_SHORT
     - 8-char hash of the last commit
     - ``4cc498b3``
   * - GIT_DATE
     - Datetime of the last commit
     - ``17-12-2024 12:47:10``
   * - GIT_NOW
     - The current date and time (not a git command at all)
     - ``19-12-2024 16:20:35``
   * - GIT_TAG
     - Most relevant tag (result of git tag)
     - ``v1.0.0``
   * - GIT_VERSION
     - Guaranteed 3-digit 1.2.3 like-string, based on `GIT_TAG`
     - ``1.0.0``
   * - GIT_BRANCH
     - Current branch name
     - ``master``
   * - GIT_DESCRIPTION
     - Most relevant tag + number of commits since then + last commit (result of git describe --tags --always)
     - ``v0.0.1-1-g4cc498b``
   * - GIT_DESCRIPTION_DIRTY
     - Same as GIT_DESCRIPTION, except it also adds the --dirty argument to mark if there were uncommitted changes
     - ``v0.0.1-1-g4cc498b-dirty``
   * - GIT_DIRTY
     - 1 if there are uncommited chances, otherwise 0
     - ``0``

When using the ``--tolerate-dirty`` flag, the ``-dirty'`` state can be repressed.
The dirty detection itself is always done by Git directly.

You can also call git commands directly using function placeholders, e.g.:

.. code-block::

   myVar  : STRING := '{{git describe --tags --abrev=4}}';


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
