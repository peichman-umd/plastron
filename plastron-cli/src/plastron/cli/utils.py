import importlib.metadata
import logging
from collections.abc import Iterable
from itertools import chain

import click
from rdflib import URIRef, Literal
from rdflib.util import from_n3

from plastron.utils import uri_or_curie

logger = logging.getLogger(__name__)


def clean_lines(*iters: Iterable[str]) -> Iterable[str]:
    """Strips surrounding whitespace and skips empty lines in the given iterables."""
    return filter(lambda s: s != '', map(str.strip, chain(*iters)))


def parse_data_property(p: str, o: str) -> tuple[URIRef, Literal]:
    """Convert a pair of strings to a URIRef predicate and Literal object."""
    return uri_or_curie(p), Literal(from_n3(o))


def parse_object_property(p: str, o: str) -> tuple[URIRef, URIRef]:
    """Convert a pair of strings to a URIRef predicate and URIRef object."""
    return uri_or_curie(p), uri_or_curie(o)


class EntryPointsGroup(click.Group):
    def __init__(self, entry_points_group: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entry_points_group = entry_points_group

    def __call__(self, *args, **kwargs):
        try:
            return self.main(*args, **kwargs)
        except RuntimeError as e:
            logger.error(str(e))
            raise SystemExit(1)

    def list_commands(self, ctx):
        base = super().list_commands(ctx)
        return base + [ep.name for ep in importlib.metadata.entry_points(group=self.entry_points_group)]

    def get_command(self, ctx, cmd_name):
        try:
            entrypoint = importlib.metadata.entry_points(group=self.entry_points_group, name=cmd_name)[0]
            return entrypoint.load()
        except IndexError:
            return super().get_command(ctx, cmd_name)
