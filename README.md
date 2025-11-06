# Azul Plugin Build Time Strings

This plugin uses the build-time-strings package to locate strings within a PE
file which contains representations of a date and time very close to the PE's
compile time. These are presumably artefacts related to the build process.

## Development Installation

To install azul-plugin-build-time-strings for development run the command
(from the root directory of this project):

```bash
pip install -e .
```

## Usage

Usage example on local files:

A POC released for CVE-2019-18935 includes a build process which generates
filenames including a build date. The resulting files include these dll names
internally. Build script::

    https://github.com/noperator/CVE-2019-18935/blob/master/build_dll.bat

We can run build-time-strings against a file built in this way to locate these times
and estimate a timezone::

```bash
$ azul-build-time-strings e51883b479720b4059a5e81d6325dcd7

    Output features:
      build_time_string: UTC -8.0 - rev_shell_2020022609163242_x86
                         UTC -8.0 - rev_shell_2020022609163242_x86.dll
```

Check `azul-plugin-build-time-strings --help` for advanced usage.

## Python Package management

This python package is managed using a `setup.py` and `pyproject.toml` file.

Standardisation of installing and testing the python package is handled through tox.
Tox commands include:

```bash
# Run all standard tox actions
tox
# Run linting only
tox -e style
# Run tests only
tox -e test
```

## Dependency management

Dependencies are managed in the requirements.txt, requirements_test.txt and debian.txt file.

The requirements files are the python package dependencies for normal use and specific ones for tests
(e.g pytest, black, flake8 are test only dependencies).

The debian.txt file manages the debian dependencies that need to be installed on development systems and docker images.

Sometimes the debian.txt file is insufficient and in this case the Dockerfile may need to be modified directly to
install complex dependencies.
