from tempfile import TemporaryDirectory

import pytest

from plastron.cli.commands.reindex import create_message, get_routing_headers
from plastron.messaging.broker import Broker, ServerTuple
from plastron.repo import RepositoryResource, Tombstone


@pytest.fixture
def broker():
    tmp_dir = TemporaryDirectory()
    return Broker(
        server=ServerTuple('localhost', 61613),
        message_store_dir=tmp_dir.name,
        destinations={
            'indexing': '/queue/indexing',
            'reindexing': '/queue/reindexing',
        },
    )


def test_create_message(plastron_context, broker):
    plastron_context.broker = broker
    resource = RepositoryResource(plastron_context.repo, '/foo')
    expected_headers = {
        'FcrepoUri': str(resource.url),
        'FcrepoPath': '/foo',
        'FcrepoUser': 'plastron',
    }
    destination, message = create_message(plastron_context, resource, routing_headers={})
    assert destination.name == '/queue/reindexing'
    assert not any(header.startswith('Camel') for header in message.headers.keys())
    for k, v in expected_headers.items():
        assert message.headers[k] == v


def test_create_message_with_delegated_user(plastron_context, broker):
    plastron_context.broker = broker
    plastron_context.delegated_user = 'johndoe'
    resource = RepositoryResource(plastron_context.repo, '/foo')
    expected_headers = {
        'FcrepoUri': str(resource.url),
        'FcrepoPath': '/foo',
        'FcrepoUser': 'johndoe',
    }
    destination, message = create_message(plastron_context, resource, routing_headers={})
    assert destination.name == '/queue/reindexing'
    assert not any(header.startswith('Camel') for header in message.headers.keys())
    for k, v in expected_headers.items():
        assert message.headers[k] == v


def test_create_message_for_tombstone(plastron_context, broker):
    plastron_context.broker = broker
    resource = Tombstone(RepositoryResource(plastron_context.repo, '/foo'))
    expected_headers = {
        'FcrepoEventName': 'delete',
        'FcrepoUri': str(resource.url),
        'FcrepoPath': '/foo',
        'FcrepoUser': 'plastron',
    }
    destination, message = create_message(plastron_context, resource, routing_headers={})
    assert destination.name == '/queue/indexing'
    assert not any(header.startswith('Camel') for header in message.headers.keys())
    for k, v in expected_headers.items():
        assert message.headers[k] == v


@pytest.fixture
def reindex_command_config():
    return {
        'REINDEX': {
            'ROUTING_HEADERS': {
                'solr': {'FcrepoIndexingDestinations': 'activemq:index.solr'},
            }
        }
    }


def test_get_routing_headers_no_config(plastron_context):
    with pytest.raises(RuntimeError) as excinfo:
        get_routing_headers(plastron_context, 'foo')

    assert "No 'COMMANDS' configuration found" in str(excinfo.value)


def test_get_routing_headers_bad_index_name(plastron_context, reindex_command_config):
    plastron_context.config['COMMANDS'] = reindex_command_config
    with pytest.raises(RuntimeError) as excinfo:
        get_routing_headers(plastron_context, 'foo')

    assert "'foo' is not a recognized index routing name." in str(excinfo.value)


def test_get_routing_headers(plastron_context, reindex_command_config):
    plastron_context.config['COMMANDS'] = reindex_command_config
    headers = get_routing_headers(plastron_context, 'solr')

    assert headers['FcrepoIndexingDestinations'] == 'activemq:index.solr'
