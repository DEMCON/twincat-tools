# TwinCAT Tools

[![Documentation](https://readthedocs.org/projects/twincat-tools/badge/?version=latest)](https://twincat-tools.readthedocs.io/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/twincat-tools)](https://pypi.org/project/twincat-tools/)
[![PyTest](https://github.com/DEMCON/twincat-tools/actions/workflows/tests.yml/badge.svg)](https://github.com/DEMCON/twincat-tools/actions)
[![codecov](https://codecov.io/gh/DEMCON/twincat-tools/graph/badge.svg?token=3NU2UNM2U0)](https://codecov.io/gh/DEMCON/twincat-tools)

This repository contains a small set of tools for developing TwinCAT projects.

## Install

Install it with pip from [pypi.org](https://pypi.org/project/twincat-tools/) with:
```
pip install twincat-tools
```

Use it as `python -m tctools.[*]`.

Note: the PyPi package named _TcTools_ is **not** affiliated with this project and is simply an unfortunate name conflict!

## Develop

### Requirements

Install package in editable mode and get the development requirements with:
```
poetry install --with dev --with doc
```

The package uses dynamic versioning.
The plugin can be added to your Poetry installation with:
```
poetry self add "poetry-dynamic-versioning[plugin]"
```

### Documentation

Documentation is built using Sphinx.
This is done automatically and hosted by [ReadTheDocs](https://about.readthedocs.com/).

### Linting

Code style is enforced with black, isort and flake8. 
Format code with:
```
isort .
black .
```
And verify code with: (flake8 extensions will also perform black and isort checks)
```
flake8 ./src ./tests
```

## Tools

See RTD documentation for full overview of usage: https://twincat-tools.readthedocs.io/latest/pages/tools.html
