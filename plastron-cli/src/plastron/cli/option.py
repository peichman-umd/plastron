"""Common CLI option definitions."""

# disable formatting so ruff won't try to put the `| kwargs` onto a separate line
# fmt: off

import click


def data_properties(**kwargs):
    """
    * Switches: `-D`, `--data-property`
    * Argument name: `data_properties`
    * Argument type: `list[tuple[str, str]]`
    """
    return click.option(
        '-D',
        '--data-property',
        'data_properties',
        **dict(
            type=(str, str),
            metavar='PREDICATE VALUE',
            multiple=True,
        ) | kwargs,
    )


def object_properties(**kwargs):
    """
    * Switches: `-O`, `--object-property`
    * Argument name: `object_properties`
    * Argument type: `list[tuple[str, str]]`
    """
    return click.option(
        '-O',
        '--object-property',
        'object_properties',
        **dict(
            type=(str, str),
            metavar='PREDICATE VALUE',
            multiple=True,
        ) | kwargs,
    )


def types(**kwargs):
    """
    * Switches: `-T`, `--rdf-type`
    * Argument name: `types`
    * Argument type: `list[str]`
    """
    return click.option(
        '-T',
        '--rdf-type',
        'types',
        **dict(
            metavar='TYPE',
            multiple=True,
        ) | kwargs,
    )


def uris_file(**kwargs):
    """
    * Switches: `-f`,`--uris-file`
    * Argument name: `uris_file`
    * Argument type: `collections.abc.Iterable[str]`
    """
    return click.option(
        '-f',
        '--uris-file',
        **dict(
            type=click.File(mode='r'),
        ) | kwargs,
    )


def binary_filename(**kwargs):
    """
    * Switches: `-b`, `--binary-file`
    * Argument name: `binary_filename`
    * Argument type: `str`
    """
    return click.option(
        '-b',
        '--binary-file',
        'binary_filename',
        **dict(
            type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
            metavar='BINARY_FILE',
        ) | kwargs,
    )


def recursive(**kwargs):
    """
    * Switches: `-R`, `--recursive`
    * Argument name: `recursive`
    * Argument type: `str`
    """
    return click.option(
        '-R',
        '--recursive',
        **dict(
            help='Include URIs found by traversing the given predicate(s).',
            metavar='PREDICATE[,PREDICATE...]',
        ) | kwargs,
    )


def dry_run(**kwargs):
    """
    * Switches: `--dry-run`
    * Argument name: `dry_run`
    * Argument type: `bool`
    """
    return click.option(
        '--dry-run',
        **dict(
            is_flag=True,
            help='Simulate the operation without modifying the repository.',
        ) | kwargs,
    )


def use_transactions(**kwargs):
    """
    Switches: `--txn/--no-txn`, `--transactions/--no-transactions`
    * Argument name: `use_transactions`
    * Argument type: `bool`
    """
    return click.option(
        '--transactions/--no-transactions',
        '--txn/--no-txn',
        'use_transactions',
        **dict(
            help='Run with or without using transactions.',
        ) | kwargs,
    )
