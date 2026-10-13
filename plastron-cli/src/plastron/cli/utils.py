from rdflib import URIRef, Literal
from rdflib.util import from_n3

from plastron.utils import uri_or_curie


def parse_data_property(p: str, o: str) -> tuple[URIRef, Literal]:
    """Convert a pair of strings to a URIRef predicate and Literal object."""
    return uri_or_curie(p), Literal(from_n3(o))


def parse_object_property(p: str, o: str) -> tuple[URIRef, URIRef]:
    """Convert a pair of strings to a URIRef predicate and URIRef object."""
    return uri_or_curie(p), uri_or_curie(o)
