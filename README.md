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

### Low-level APIs

* **[plastron-client](plastron-client)**: The Fedora repository API client
* **[plastron-messaging](plastron-messaging)**: STOMP message models and 
  message broker connection handling
* **[plastron-rdf](plastron-rdf)**: RDF-to-Python property mapping
* **[plastron-utils](plastron-utils)**: Namespace definitions 
  and miscellaneous utilities

The intent is that these distribution packages are independently useful,
either as tools that can be run or libraries to be included in other projects.

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

Clone the repo, and use [uv] to install the dependencies, including those 
in all the optional dependency extra groups.

```zsh
git clone git@github.com:umd-lib/plastron.git
cd plastron

uv sync --all-extras
```

### Testing

Plastron uses the [pytest] test framework for its tests:

```zsh
uv run pytest
```

See the [testing documentation](docs/testing.md) for more
information.

## API Documentation

To generate API documentation from the code, use [pdoc]:

```zsh
uv run pdoc plastron
```

The generated (and live-updating) HTML documentation will be available at 
<http://localhost:8080/plastron.html>.

## Name

> The plastron is the nearly flat part of the shell structure of a turtle,
> what one would call the belly or ventral surface of the shell.

Source: [Wikipedia](https://en.wikipedia.org/wiki/Turtle_shell#Plastron)

## License

See the [LICENSE](LICENSE.md) file for license rights and
limitations (Apache 2.0).

[uv]: https://docs.astral.sh/uv/
[pytest]: https://pypi.org/project/pytest/
[pyenv]: https://github.com/pyenv/pyenv
[pdoc]: https://pdoc.dev/
