# TwinCAT Tools

This repository contains a small set of tools for developing TwinCAT projects.

## XML Sorter

TwinCAT saves its project files somewhat arbitrarily, the order of elements is changed seemingly at random.
Use this XML sorter before committing your changes to fix the XML layout and keep your Git history more clean.

Usage:

```cmd
python -m tctools.xml_sort [file or folder, ...] -r --ext tsproj xti plcproj --skip-nodes Device DeploymentEvents TcSmItem DataType
```

Add `--help` for full instructions.

### Notes

* Nodes with the attribute `xml:space="preserve"` are not touched

### Differences with Ruud's XmlSorter

The precursor of this script is the XmlSorter made by Ruud, written in C#:
https://github.com/DEMCON/XmlSorter

There are a couple of difference between this sorter and Ruud's:

* The root attribute `xmlns:xsi` cannot be sorted
  * This is because `lxml` does not show it an attribute.
* This sorter will prefer self-closing tags where content is emtpy, instead of leaving them as they were.
  * This is a consequence of `lxml`, it cannot identify self-closing tags upon reading.
  * The self-closing tags also do not have a trailing space before the final "/>".
* Unicode characters are written as `#...;` instead of literals.
  * Something `lxml` just seems to do.

**None** of these appear problematic for TwinCAT.
Projects can be opened and built again as expected, and when saved again the file will be as TwinCAT likes it.

## Auto Formatter

Use this to make consistent use of spaces/tabs.
Visual Studio with PLC doesn't do a lot of the things that other IDEs do, like removing trailing whitespace and making 
consistent usage of spaces / tabs.
This tool is meant to supplement this.

Specify your preferences with an `.editorconfig` [file](https://editorconfig.org/), as you would for other projects.
An example:

```
[*.TcPOU]
indent_style = space
indent_size = 4
```

Usage:

```cmd
python -m tctools.format [file or folder, ...] [--check]
```

Add `--help` for full instructions.

### Valid options

The following `.editorconfig` fields are considered:

* `tab_style`
  * If style is set space, any tab character will be replaced
  * If style is set to tab, any `tab_width`-number of spaces will be replaced by a tab
* `trim_trailing_whitespace`
  * If true, whitespace at the end of lines is removed
