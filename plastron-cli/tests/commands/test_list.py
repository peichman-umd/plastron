import httpretty
from rdflib import Graph

from plastron.cli import main


@httpretty.activate
def test_list_command(runner, config_file_name, datadir, simulate_repo):
    graph = Graph().parse(file=(datadir / 'graph.ttl').open())
    simulate_repo(graph)
    result = runner.invoke(main, ['-c', config_file_name, 'ls', '/container'])
    assert len(result.stdout.splitlines()) == 2
    assert 'http://localhost:9999/container/1\n' in result.stdout
    assert 'http://localhost:9999/container/2\n' in result.stdout


@httpretty.activate
def test_list_long_command(runner, config_file_name, datadir, simulate_repo):
    graph = Graph().parse(file=(datadir / 'graph.ttl').open())
    simulate_repo(graph)
    result = runner.invoke(main, ['-c', config_file_name, 'ls', '--long', '/container'])
    assert len(result.stdout.splitlines()) == 2
    assert 'http://localhost:9999/container/1 Foobar\n' in result.stdout
    assert 'http://localhost:9999/container/2 Moonpig\n' in result.stdout
