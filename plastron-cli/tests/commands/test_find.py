import httpretty
import pytest
from click.testing import CliRunner
from rdflib import Graph, Literal

from plastron.cli import main
from plastron.cli.commands.find import find
from plastron.namespaces import dcterms, ldp, pcdm, rdf


@pytest.mark.parametrize(
    ['matcher', 'properties', 'expected_count'],
    [
        (all, [], 3),
        (all, [(rdf.type, pcdm.Object)], 1),
        (all, [(rdf.type, pcdm.Object), (dcterms.title, Literal('Moonpig'))], 0),
        (any, [(rdf.type, pcdm.Object), (dcterms.title, Literal('Moonpig'))], 2),
    ],
)
@httpretty.activate
def test_find(datadir, repo, simulate_repo, matcher, properties, expected_count):
    graph = Graph().parse(file=(datadir / 'graph.ttl').open())
    simulate_repo(graph)
    resources = list(
        find(
            start_resource=repo['/container'],
            matcher=matcher,
            traverse=[ldp.contains],
            properties=properties,
        )
    )
    assert len(resources) == expected_count


@pytest.mark.parametrize(
    ('args', 'expected_paths'),
    [
        (
            ['--recursive', 'ldp:contains', '/container'],
            ['/container', '/container/1', '/container/2'],
        ),
        (
            ['--recursive', 'ldp:contains', '--rdf-type', 'pcdm:Object', '/container'],
            ['/container/1'],
        ),
        (
            [
                '--recursive',
                'ldp:contains',
                '--data-property',
                'dcterms:title',
                'Moonpig',
                '--rdf-type',
                'pcdm:Object',
                '--match-any',
                '/container',
            ],
            ['/container/1', '/container/2'],
        ),
    ],
)
@httpretty.activate
def test_find_command(datadir, shared_datadir, simulate_repo, args, expected_paths):
    graph = Graph().parse(file=(datadir / 'graph.ttl').open())
    simulate_repo(graph)
    runner = CliRunner()
    result = runner.invoke(main, ['--config', str(shared_datadir / 'plastron.yml'), 'find', *args])
    assert len(result.stdout.splitlines()) == len(expected_paths)
    for path in expected_paths:
        assert f'http://localhost:9999{path}\n' in result.stdout
