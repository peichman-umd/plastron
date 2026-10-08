"""Common CLI argument definitions."""

import click


def uris(**kwargs):
    """
    * Argument name: `uris`
    * Argument type: `list[str]`
    """
    return click.argument(
        'uris',
        **dict(
            nargs=-1,
            metavar='[URI[ URIs...]]',
        ) | kwargs,
    )
