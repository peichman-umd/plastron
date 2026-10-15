import pytest
from rdflib import Literal, URIRef

from plastron.cli.utils import parse_object_property, parse_data_property, clean_lines
from plastron.namespaces import dcterms, rdf, pcdm


@pytest.mark.parametrize(
    ('iterables', 'expected_list'),
    [
        ([], []),
        ([['foo', 'bar']], ['foo', 'bar']),
        ([['foo'], ['bar']], ['foo', 'bar']),
        ([['foo\n', 'bar\n']], ['foo', 'bar']),
        ([[' foo\n', ' bar\n']], ['foo', 'bar']),
        ([[' foo\n', '\n', ' bar\n']], ['foo', 'bar']),
    ]
)
def test_clean_lines(iterables, expected_list):
    assert list(clean_lines(*iterables)) == expected_list


@pytest.mark.parametrize(
    ('p', 'o', 'expected'),
    [
        ('dcterms:title', 'Foobar', (dcterms.title, Literal('Foobar'))),
        ('dcterms:title', '"der Hund"@de', (dcterms.title, Literal('der Hund', lang='de'))),
    ],
)
def test_parse_data_property(p, o, expected):
    assert parse_data_property(p, o) == expected


@pytest.mark.parametrize(
    ('p', 'o', 'expected'),
    [
        ('rdf:type', 'pcdm:Object', (rdf.type, pcdm.Object)),
        ('dcterms:creator', 'https://www.lib.umd.edu/', (dcterms.creator, URIRef('https://www.lib.umd.edu/'))),
        ('dcterms:creator', '<https://www.lib.umd.edu/>', (dcterms.creator, URIRef('https://www.lib.umd.edu/'))),
    ],
)
def test_parse_object_property(p, o, expected):
    assert parse_object_property(p, o) == expected
