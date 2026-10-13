from unittest.mock import MagicMock

import click

from plastron.cli import plastron_command
from plastron.cli.commands.unpublish import unpublish_command
from plastron.client import Client, Endpoint
from plastron.client.utils import TypedText
from plastron.context import PlastronContext
from plastron.models.umd import Item
from plastron.namespaces import umdaccess
from plastron.repo import Repository, RepositoryError
from plastron.repo.publish import PublishableResource


def get_mock_context(obj):
    endpoint = Endpoint('http://fcrepo-local:8080/fcrepo/rest')
    mock_client = MagicMock(spec=Client, endpoint=endpoint)
    mock_client.get_description.return_value = TypedText('application/n-triples', '')
    mock_repo = MagicMock(spec=Repository, client=mock_client, endpoint=endpoint)
    resource = PublishableResource(repo=mock_repo, path='/foo')
    resource.describe = lambda _: obj
    mock_repo.__getitem__.return_value = resource
    return MagicMock(
        spec=PlastronContext,
        repo=mock_repo,
        get_public_url=lambda uri: uri.replace('fcrepo-local:8080/fcrepo/rest', 'digital-local'),
    )


def test_unpublish():
    obj = Item(rdf_type=umdaccess.Published)
    ctx = click.Context(command=plastron_command, obj=get_mock_context(obj))
    ctx.invoke(unpublish_command, uris=['http://fcrepo-local:8080/fcrepo/rest/foo'])

    assert umdaccess.Published not in obj.rdf_type.values


def test_unpublish_hidden():
    obj = Item(rdf_type=umdaccess.Published)
    ctx = click.Context(command=plastron_command, obj=get_mock_context(obj))
    ctx.invoke(unpublish_command, uris=['http://fcrepo-local:8080/fcrepo/rest/foo'], force_hidden=True)

    assert umdaccess.Published not in obj.rdf_type.values
    assert umdaccess.Hidden in obj.rdf_type.values


def test_unpublish_make_visible():
    obj = Item(rdf_type=[umdaccess.Published, umdaccess.Hidden])
    ctx = click.Context(command=plastron_command, obj=get_mock_context(obj))
    ctx.invoke(unpublish_command, uris=['http://fcrepo-local:8080/fcrepo/rest/foo'], force_visible=True)

    assert umdaccess.Published not in obj.rdf_type.values
    assert umdaccess.Hidden not in obj.rdf_type.values


def test_unpublish_repo_error(caplog):
    mock_repo = MagicMock(spec=Repository)
    mock_repo.__getitem__.side_effect = RepositoryError('something bad')

    ctx = click.Context(command=plastron_command, obj=MagicMock(spec=PlastronContext, repo=mock_repo))
    ctx.invoke(unpublish_command, uris=['http://fcrepo-local:8080/fcrepo/rest/foo'])

    assert 'Unable to retrieve http://fcrepo-local:8080/fcrepo/rest/foo: something bad' in caplog.messages
