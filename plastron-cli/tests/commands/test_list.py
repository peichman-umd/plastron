import responses
from rdflib import Graph

from plastron.cli import plastron_command


@responses.activate
def test_list_command(cli_runner, config_file_name, shared_datadir, simulate_repo):
    graph = Graph().parse(file=(shared_datadir / 'graph.ttl').open())
    simulate_repo(graph)
    result = cli_runner.invoke(plastron_command, ['-c', config_file_name, 'ls', '/container'])
    assert len(result.stdout.splitlines()) == 2
    assert 'http://example.com/fcrepo/rest/container/1\n' in result.stdout
    assert 'http://example.com/fcrepo/rest/container/2\n' in result.stdout


@responses.activate
def test_list_long_command(cli_runner, config_file_name, shared_datadir, simulate_repo):
    graph = Graph().parse(file=(shared_datadir / 'graph.ttl').open())
    simulate_repo(graph)
    result = cli_runner.invoke(plastron_command, ['-c', config_file_name, 'ls', '--long', '/container'])
    assert len(result.stdout.splitlines()) == 2
    assert 'http://example.com/fcrepo/rest/container/1 Foobar\n' in result.stdout
    assert 'http://example.com/fcrepo/rest/container/2 Moonpig\n' in result.stdout
