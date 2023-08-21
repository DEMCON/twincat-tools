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

### Auto Formatter

Use this to to make consistent use of spaces/tabs.

Usage:

```cmd
python -m tctools.format [--project=<file>] [--files=<files>]
```

Add `--help` for full instructions.
