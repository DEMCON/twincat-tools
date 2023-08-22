# TwinCAT Tools

This repository contains a small set of tools for developing TwinCAT projects.

## Tools

### XML Sorter

TwinCAT saves its project files somewhat arbitrarily, the order of elements is changed seemingly at random.
Use this XML sorter before committing your changes to fix the XML layout and keep your Git history more clean.

Usage:

```cmd
python -m tctools.xml_sort [--project=<file>] [--files=<files>]
```

Add `--help` for full instructions.

#### Differences with Ruud's XmlSorter

The precursor of this script is the XmlSorter made by Ruud, written in C#:
https://github.com/DEMCON/XmlSorter

There are a couple of difference between this sorter and Ruud's:

* The root attribute `xmlns:xsi` cannot be sorted
  * This is because `lxml` does not show it an attribute.
* This sorter will prefer self-closing tags where content is emtpy, instead of leaving them as they were.
  * This is a consequence of `lxml`, it cannot identify self-closing tags upon reading.
* Unicode characters are written as `#...;` instead of literals.
  * Something `lxml` just seems to do.

**None** is these appear problematic for TwinCAT.
Projects can be opened and built again as expected, and when saved again the file will be as TwinCAT likes it.

### Auto Formatter

Use this to to make consistent use of spaces/tabs.

Usage:

```cmd
python -m tctools.format [--project=<file>] [--files=<files>]
```

Add `--help` for full instructions.
