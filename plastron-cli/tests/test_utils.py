from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock, patch
from uuid import uuid4

import click
import pytest
from rdflib import Literal, URIRef

from conftest import cli_runner
from plastron.cli.utils import parse_object_property, parse_data_property, clean_lines, EntryPointsGroup
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


@dataclass
class MockEntryPoint:
    name: str

    def load(self):
        return self.name


@patch('importlib.metadata.entry_points')
def test_entry_points_group_list_commands(mock_entry_points):
    mock_entry_points.return_value = [
        MockEntryPoint(name='foo'),
        MockEntryPoint(name='bar'),
    ]
    group = EntryPointsGroup('commands')
    assert len(group.list_commands(Mock(spec=click.Context))) == 2


@patch('importlib.metadata.entry_points')
def test_entry_points_group_get_command(mock_entry_points):
    mock_entry_points.return_value = {
        'foo': MockEntryPoint(name='foo'),
        'bar': MockEntryPoint(name='bar'),
    }
    group = EntryPointsGroup('commands')
    assert group.get_command(Mock(spec=click.Context), 'foo') == 'foo'


@patch('importlib.metadata.entry_points')
def test_entry_points_group_get_command_not_found(mock_entry_points):
    mock_entry_points.return_value = {
        'foo': MockEntryPoint(name='foo'),
        'bar': MockEntryPoint(name='bar'),
    }
    group = EntryPointsGroup('commands')
    assert group.get_command(Mock(spec=click.Context), 'FAKE_COMMAND') is None


def test_command_exception(cli_runner):
    nonce = str(uuid4())

    class FaultyCommand(EntryPointsGroup):
        def main(
            self,
            args: Sequence[str] | None = None,
            prog_name: str | None = None,
            complete_var: str | None = None,
            standalone_mode: bool = True,
            windows_expand_args: bool = True,
            ** extra: Any,
        ):
            raise RuntimeError(nonce)

    cmd = FaultyCommand(entry_points_group='commands')
    with pytest.raises(SystemExit, match='1'):
        cmd()
