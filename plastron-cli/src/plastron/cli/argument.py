"""Common CLI argument definitions."""

# disable formatting so ruff won't try to put the `| kwargs` onto a separate line
# fmt: off

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
