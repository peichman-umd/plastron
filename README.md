# Plastron

Tools for working with a Fedora 4 repository.

## Architecture

Plastron is composed of several distribution packages, arranged in three 
layers:

### Applications

* **[plastron-cli](plastron-cli)**: Command-line tool. Also includes the
  handler classes for the `load` command
* **[plastron-stomp](plastron-stomp)**: STOMP daemon for handling
  asynchronous operations
* **[plastron-web](plastron-web)**: Web application for handling
  synchronous operations

### High-Level APIs

* **[plastron-models](plastron-models)**: Content models, CSV
  serialization
* **[plastron-repo](plastron-repo)**: Repository operations and structural
  models (LDP, PCDM, Web Annotations, etc.)
* **[plastron-jobs](plastron-jobs)**: Batch repository operations
  (import, export, publish, etc.)

### Low-level APIs

* **[plastron-client](plastron-client)**: The Fedora repository API client
* **[plastron-messaging](plastron-messaging)**: STOMP message models and 
  message broker connection handling
* **[plastron-rdf](plastron-rdf)**: RDF-to-Python property mapping
* **[plastron-utils](plastron-utils)**: Namespace definitions 
  and miscellaneous utilities

The intent is that these distribution packages are independently useful,
either as tools that can be run or libraries to be included in other projects.

### Package Dependency Diagram

This "layer cake" style diagram represents the dependencies among the 
`plastron-*` distribution packages:

```mermaid
block-beta
  columns 6
  cli:2 web:2 stomp:2
  jobs:6
  repo:4 messaging:2
  client:2 models:2 space:2
  space:2 rdf utils space:2
```

## Installation

Requires Python 3.8+

To install just the API libraries (low- and high-level):

```zsh
pip install plastron
```

To install the applications as well:

```zsh
# individually
pip install 'plastron[cli]'
pip install 'plastron[stomp]'
pip install 'plastron[web]'

# all together
pip install 'plastron[cli,stomp,web]'
```

## Running

* [Command-line client](plastron-cli/README.md)
* [STOMP daemon](plastron-stomp/README.md)
* [HTTP webapp](plastron-web/README.md)

## Development

This repository includes a [.python-version](.python-version) file. If you are
using a tool like [pyenv] to manage your Python versions, it will select
an installed Python 3.8 for you.

To install Plastron in [development mode], do the following:

```zsh
git clone git@github.com:umd-lib/plastron.git
cd plastron
python -m venv --prompt "plastron-py$(cat .python-version)" .venv
source .venv/bin/activate
pip install \
    -e './plastron-utils[test]' \
    -e './plastron-client[test]' \
    -e './plastron-rdf[test]' \
    -e './plastron-messaging[test]' \
    -e './plastron-models[test]' \
    -e './plastron-repo[test]' \
    -e './plastron-jobs[test]' \
    -e './plastron-web[test]' \
    -e './plastron-stomp[test]' \
    -e './plastron-cli[test]'
```

This allows for in-place editing of Plastron's source code in the git
repository (i.e., it is not locked away in a Python site-packages directory
structure).

### Testing

Plastron uses the [pytest] test framework for its tests.

```bash
pytest
```

See the [testing documentation](docs/testing.md) for more
information.

## API Documentation

To generate API documentation from the code, use [pdoc]:

```bash
pip install pdoc
```

To use the built-in, live-reloading web server to generate and browse the 
documentation, use:

```bash
pdoc plastron
```

The generated HTML documentation will be available at 
<http://localhost:8080/plastron.html>.

## Name

> The plastron is the nearly flat part of the shell structure of a turtle,
> what one would call the belly or ventral surface of the shell.

Source: [Wikipedia](https://en.wikipedia.org/wiki/Turtle_shell#Plastron)

## License

See the [LICENSE](LICENSE.md) file for license rights and
limitations (Apache 2.0).

[development mode]: https://packaging.python.org/tutorials/installing-packages/#installing-from-vcs
[pytest]: https://pypi.org/project/pytest/
[pyenv]: https://github.com/pyenv/pyenv
[pdoc]: https://pdoc.dev/
