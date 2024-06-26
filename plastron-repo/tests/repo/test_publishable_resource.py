import dataclasses
from random import randint
from unittest.mock import MagicMock

import pytest

from plastron.client import Endpoint, Client, TypedText
from plastron.handles import HandleInfo, HandleServerError
from plastron.namespaces import umdaccess
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Repository, RepositoryError
from plastron.repo.publish import PublishableResource, get_publication_status


@pytest.mark.parametrize(
    ('obj', 'expected_status'),
    [
        (RDFResource(), 'Unpublished'),
        (RDFResource(rdf_type=umdaccess.Hidden), 'UnpublishedHidden'),
        (RDFResource(rdf_type=umdaccess.Published), 'Published'),
        (RDFResource(rdf_type=[umdaccess.Published, umdaccess.Hidden]), 'PublishedHidden'),
    ],
)
def test_get_publication_status(obj, expected_status):
    assert get_publication_status(obj) == expected_status


# TODO: this should go into a common library
class MockHandleClient:
    default_repo = 'fcrepo'

    GET_HANDLE_LOOKUP = {
        # existing handle with fcrepo target URL
        '1903.1/123': HandleInfo(
            exists=True,
            prefix='1903.1',
            suffix='123',
            url='http://digital-local/foo',
        ),
        # existing handle with fedora2 target URL
        # if publishing the resource with this handle,
        # should call the handle server to update the
        # target URL
        '1903.1/456': HandleInfo(
            exists=True,
            prefix='1903.1',
            suffix='456',
            url='http://fedora2-local/bar',
        ),
        # there is no handle with this prefix/suffix pair
        '1903.1/789': HandleInfo(
            exists=False,
        ),
    }
    FIND_HANDLE_LOOKUP = {
        # this fcrepo resource has a handle and its target
        # URL points to the correct public URL
        'http://fcrepo-local:8080/fcrepo/rest/foo': HandleInfo(
            exists=True,
            prefix='1903.1',
            suffix='123',
            url='http://digital-local/foo',
        ),
        # this fcrepo resource has a handle and its target
        # URL needs to be updated to the correct public URL
        'http://fcrepo-local:8080/fcrepo/rest/bar': HandleInfo(
            exists=True,
            prefix='1903.1',
            suffix='456',
            url='http://fedora2-local/bar',
        ),
    }

    def get_info(self, prefix: str, suffix: str) -> HandleInfo:
        return self.GET_HANDLE_LOOKUP.get(f'{prefix}/{suffix}', HandleInfo(exists=False))

    def find_handle(self, repo_id: str, _repo: str = None) -> HandleInfo:
        return self.FIND_HANDLE_LOOKUP.get(repo_id, HandleInfo(exists=False))

    @staticmethod
    def create_handle(repo_id: str, url: str, prefix: str = None, _repo: str = None) -> HandleInfo:
        if repo_id.endswith('NO_HANDLE'):
            raise HandleServerError('no handle')
        return HandleInfo(exists=True, prefix=prefix, suffix=str(randint(1000, 10000)), url=url)

    @staticmethod
    def update_handle(handle: HandleInfo, **fields) -> HandleInfo:
        return dataclasses.replace(handle, **fields)


@pytest.fixture
def endpoint():
    return Endpoint('http://fcrepo-local:8080/fcrepo/rest')


@pytest.fixture
def mock_client(endpoint):
    return mock_client


@pytest.fixture
def mock_repo(endpoint):
    def _mock_repo(path, handle):
        mock_client = MagicMock(spec=Client, endpoint=endpoint)
        if handle is not None:
            value = (
                f'<{endpoint.url}{path}> '
                '<http://purl.org/dc/terms/identifier> '
                f'"{handle}"^^<http://vocab.lib.umd.edu/datatype#handle> .\n'
            )
        else:
            value = ''

        mock_client.get_description.return_value = TypedText(media_type='application/n-triples', value=value)
        return MagicMock(spec=Repository, client=mock_client, endpoint=endpoint)

    return _mock_repo


@pytest.mark.parametrize(
    ('fcrepo_path', 'existing_handle', 'expected_suffix', 'expected_url'),
    [
        # existing handle with fcrepo target URL
        (
            '/foo',
            HandleInfo(exists=True, prefix='1903.1', suffix='123', url='http://digital-local/foo'),
            '123',
            'http://digital-local/foo',
        ),
        # existing handle with fedora2 target URL; if publishing the resource with this handle,
        # should call the handle server to update the target URL
        (
            '/bar',
            HandleInfo(exists=True, prefix='1903.1', suffix='456', url='http://fedora2-local/bar'),
            '456',
            'http://digital-local/bar',
        ),
    ]
)
def test_existing_handle(mock_repo, fcrepo_path, existing_handle, expected_suffix, expected_url):
    mock_client = MockHandleClient()  # resolver={existing_handle.hdl_uri: existing_handle})
    resource = PublishableResource(
        repo=mock_repo(path=fcrepo_path, handle=existing_handle.hdl_uri),
        path=fcrepo_path
    ).read()
    handle = resource.publish(mock_client, expected_url)
    assert handle.suffix == expected_suffix
    assert handle.url == expected_url


def test_missing_handle(mock_repo):
    # resource metadata has a handle value, but that handle is not found in the handle service
    # should raise a RepositoryError
    mock_handle_client = MockHandleClient()
    resource = PublishableResource(
        repo=mock_repo(path='/abc', handle='hdl:1903.1/789'),
        path='/abc',
    ).read()
    with pytest.raises(RepositoryError) as e:
        resource.publish(mock_handle_client, 'http://digital-local/abc')
    assert str(e.value).startswith('Unable to publish')


def test_mint_new_handle(mock_repo):
    # resource metadata has no handle value, so we create one in the handle service
    mock_handle_client = MockHandleClient()
    resource = PublishableResource(
        repo=mock_repo(path='/def', handle=None),
        path='/def',
    ).read()
    handle = resource.publish(mock_handle_client, 'http://digital-local/def')
    assert handle.url == 'http://digital-local/def'
    assert 1000 <= int(handle.suffix) <= 10000


def test_error_creating_handle(mock_repo):
    # resource has no handle, and handle client fails to create a handle
    mock_handle_client = MockHandleClient()
    resource = PublishableResource(
        repo=mock_repo(path='/NO_HANDLE', handle=None),
        path='/NO_HANDLE',
    ).read()
    with pytest.raises(RepositoryError) as e:
        resource.publish(mock_handle_client, 'http://digital-local/abc')
    assert str(e.value).startswith('Unable to publish')
