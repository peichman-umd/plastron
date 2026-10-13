import re
from collections.abc import Callable
from uuid import uuid4

import pytest
import responses
from click.testing import CliRunner
from rdflib import Graph
from responses import HEAD, GET, POST, PUT, DELETE

from plastron.client import Client, Endpoint
from plastron.client.auth import get_authenticator
from plastron.client.utils import fedora_tx
from plastron.context import PlastronContext
from plastron.namespaces import fedora
from plastron.repo import Repository


@pytest.fixture
def repo_base_config():
    """Required parameters for Repository configuration"""
    return {'REST_ENDPOINT': 'http://example.com/fcrepo/rest', 'AUTH_TOKEN': 'foobar'}


@pytest.fixture
def plastron_context(repo_base_config, repo):
    return PlastronContext(config={'REPOSITORY': repo_base_config})


@pytest.fixture
def endpoint(repo_base_config):
    return Endpoint(
        url=repo_base_config['REST_ENDPOINT'],
    )


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def config_file_name(shared_datadir):
    return str(shared_datadir / 'plastron.yml')


@pytest.fixture
def client(repo_base_config, endpoint) -> Client:
    return Client(
        endpoint=endpoint,
        auth=get_authenticator(repo_base_config),
    )


@pytest.fixture
def repo(client) -> Repository:
    return Repository(client=client)


@pytest.fixture
def register_root(repo: Repository):
    txn_triple = f'<{repo["/"].url}> <{fedora.hasTransactionProvider}> <{repo["/fcr:tx"].url}> .'

    def _register_root(status: int = 200):
        responses.add(
            method=HEAD,
            url=repo.endpoint.url,
            status=status,
        )
        responses.add(
            method=GET,
            url=repo.endpoint.url,
            status=status,
            content_type='application/n-triples',
            body=txn_triple,
        )
        responses.add(
            method=HEAD,
            url=repo['/'].url,
            status=status,
        )
        responses.add(
            method=GET,
            url=repo['/'].url,
            status=status,
            content_type='application/n-triples',
            body=txn_triple,
        )

    return _register_root


@pytest.fixture
def simulate_repo(register_root) -> Callable[[Graph], None]:
    """Pytest fixture that uses HTTPretty to simulate a read-only repository.
    The repository is defined using a Graph. Each unique subject in that graph
    is assumed to be its own resource. Each resource will respond to HEAD and
    GET requests with 200 OK and Content-Type application/n-triples."""

    def _register_repo(graph: Graph):
        register_root()
        subjects = set(graph.subjects())
        for subject in subjects:
            resource_graph = Graph()
            for triple in graph.triples((subject, None, None)):
                resource_graph.add(triple)
            body = resource_graph.serialize(format='application/n-triples')
            responses.add(
                method=HEAD,
                url=subject,
                status=200,
                content_type='application/n-triples',
            )
            responses.add(
                method=GET,
                url=subject,
                status=200,
                body=body,
                content_type='application/n-triples',
            )

    return _register_repo


@pytest.fixture
def register_resource():
    def _register_resource(url: str | re.Pattern, response_args: dict[str, dict]):
        for method, kwargs in response_args.items():
            responses.add(method=method, url=url, **kwargs)
    return _register_resource


@pytest.fixture
def register_transactions(register_root, repo):
    def _register_transactions():
        register_root()
        txn_id = str(uuid4())
        txn_url = repo[f'/tx:{txn_id}'].url
        # creating a new transaction
        responses.add(
            url=repo['/fcr:tx'].url,
            method=POST,
            status=201,
            headers={
                'Location': txn_url,
            },
        )
        # maintenance action
        responses.add(
            url=txn_url,
            method=POST,
            status=204,
        )
        # commit, and rollback actions
        responses.add(
            url=re.compile(str(txn_url) + '/fcr:tx/fcr:(commit|rollback)'),
            method=POST,
            status=204,
        )
        return txn_url

    return _register_transactions


@pytest.fixture
def register_f6_transactions(register_root, register_resource, repo):
    def _register_f6_transactions():
        register_root()
        txn_id = str(uuid4())
        txn_url = repo[f'/fcr:tx/{txn_id}'].url
        # creating a new transaction
        responses.add(
            url=repo['/fcr:tx'].url,
            method=POST,
            status=201,
            headers={
                'Link': f'<{txn_url}>; rel="{fedora_tx.commitEndpoint}"',
                'Location': txn_url,
            },
        )
        register_resource(
            url=txn_url,
            response_args={
                # maintain
                POST: {'status': 204},
                # commit
                PUT: {'status': 204},
                # rollback
                DELETE: {'status': 204},
            },
        )
        return txn_url

    return _register_f6_transactions


@pytest.fixture
def register_binary(repo, register_resource):
    def _register_binary(path: str):
        url = str(repo[path].url)
        description_url = f'{url}/fcr:metadata'
        register_resource(
            url=url,
            response_args={
                HEAD: {
                    'status': 200,
                    'headers': {
                        'Link': f'<{description_url}>; rel="describedby',
                    },
                },
                GET: {
                    'status': 200,
                    'body': '',
                    'headers': {
                        'Link': f'<{description_url}>; rel="describedby',
                    },
                },
                PUT: {'status': 204, 'body': ''},
            },
        )
        register_resource(
            url=description_url,
            response_args={
                HEAD: {'status': 200},
                GET: {'status': 200, 'body': '', 'content_type': 'application/n-triples'},
                PUT: {'status': 204, 'body': ''},
            },
        )
        return url, description_url
    return _register_binary


@pytest.fixture
def resource_not_found():
    return {
        HEAD: {'status': 404},
        GET: {'status': 404, 'body': ''},
        DELETE: {'status': 404},
    }
