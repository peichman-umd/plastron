import logging
from collections.abc import Iterable, Mapping
from os import getpid, uname

import click

from plastron.cli import argument, option, version
from plastron.cli.utils import clean_lines
from plastron.context import PlastronContext
from plastron.messaging.broker import Destination
from plastron.messaging.messages import Message
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Tombstone, RepositoryResource
from plastron.utils import parse_predicate_list

logger = logging.getLogger(__name__)


@click.command(help='Reindex objects in the repository')
@option.recursive()
@click.option(
    '-i',
    '--index',
    help='Configuration key for the index to target; defaults to "all".',
    metavar='KEY',
    default='all',
)
@option.uris_file()
@argument.uris()
@click.help_option('-h', '--help')
@click.pass_context
def reindex_command(
    ctx: click.Context,
    recursive: str | None,
    index: str,
    uris_file: Iterable[str] | None,
    uris: list[str],
):
    routing_headers = get_routing_headers(ctx.obj, index)
    logger.info(f'Indexing to {index}')
    if ctx.obj.broker.connect(client_id=f'plastron/{version}-{uname().nodename}-{getpid()}'):
        traverse = parse_predicate_list(recursive) if recursive is not None else []

        for uri in clean_lines(uris_file or [], uris):
            for resource in ctx.obj.repo[uri].walk(traverse=traverse, include_tombstones=True):
                logger.info(f'Reindexing {resource.url}')
                destination, message = create_message(ctx.obj, resource, routing_headers)
                destination.send(message)

        ctx.obj.broker.disconnect()
    else:
        raise RuntimeError(f'STOMP connection failed for {ctx.obj.broker}')


def get_routing_headers(plastron_context: PlastronContext, index_key: str) -> dict[str, str]:
    try:
        all_routing_headers = plastron_context.config['COMMANDS']['REINDEX']['ROUTING_HEADERS']
    except KeyError as e:
        raise RuntimeError(f'No {e} configuration found') from e

    try:
        return all_routing_headers[index_key]
    except KeyError as e:
        raise RuntimeError(
            f'{e} is not a recognized index routing name. Use one of: {", ".join(all_routing_headers.keys())}'
        ) from e


def create_message(
    plastron_context: PlastronContext,
    resource: RepositoryResource | Tombstone,
    routing_headers: Mapping[str, str],
) -> tuple[Destination, Message]:
    username = plastron_context.delegated_user or 'plastron'
    if isinstance(resource, Tombstone):
        logger.info(f'Resource {resource.url} has been removed, sending message to delete from indexes')
        return (
            plastron_context.broker.destination('indexing'),
            Message(
                headers={
                    'FcrepoEventName': 'delete',
                    'FcrepoUri': resource.url,
                    'FcrepoPath': resource.path,
                    'FcrepoUser': username,
                    **routing_headers,
                },
                persistent='true',
            ),
        )
    else:
        types = ','.join(resource.describe(RDFResource).rdf_type.values)
        return (
            plastron_context.broker.destination('reindexing'),
            Message(
                headers={
                    'FcrepoUri': resource.url,
                    'FcrepoPath': resource.path,
                    'FcrepoResourceType': types,
                    'FcrepoUser': username,
                    **routing_headers,
                },
                persistent='true',
            ),
        )
