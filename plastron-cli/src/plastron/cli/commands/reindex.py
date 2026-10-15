import logging
from os import getpid, uname

import click

from plastron.cli import argument, option, version
from plastron.cli.utils import clean_lines
from plastron.context import PlastronContext
from plastron.messaging.messages import Message
from plastron.rdfmapping.resources import RDFResource
from plastron.repo import Tombstone
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
@option.uris_file(help='File containing URIs of objects to reindex.')
@argument.uris(help='URIs of repository objects to reindex.')
@click.help_option('-h', '--help')
@click.pass_context
def reindex_command(
    ctx: click.Context,
    recursive: str | None,
    index: str,
    uris_file,
    uris: list[str],
):
    routing_headers = get_routing_headers(ctx.obj, index)
    logger.info(f'Indexing to {index}')
    if ctx.obj.broker.connect(client_id=f'plastron/{version}-{uname().nodename}-{getpid()}'):
        reindexing_queue = ctx.obj.broker.destination('reindexing')
        indexing_queue = ctx.obj.broker.destination('indexing')
        username = ctx.obj.delegated_user or 'plastron'
        traverse = parse_predicate_list(recursive) if recursive is not None else []

        for uri in clean_lines(uris_file or [], uris):
            for resource in ctx.obj.repo[uri].walk(traverse=traverse, include_tombstones=True):
                logger.info(f'Reindexing {resource.url}')
                if isinstance(resource, Tombstone):
                    logger.info(f'Resource {resource.url} has been removed, sending message to delete from indexes')
                    indexing_queue.send(
                        Message(
                            headers={
                                'CamelFcrepoEventName': 'delete',
                                'CamelFcrepoUri': resource.url,
                                'CamelFcrepoPath': resource.path,
                                'CamelFcrepoUser': username,
                                **routing_headers,
                            },
                            persistent='true',
                        )
                    )
                else:
                    types = ','.join(resource.describe(RDFResource).rdf_type.values)
                    reindexing_queue.send(
                        Message(
                            headers={
                                'CamelFcrepoUri': resource.url,
                                'CamelFcrepoPath': resource.path,
                                'CamelFcrepoResourceType': types,
                                'CamelFcrepoUser': username,
                                **routing_headers,
                            },
                            persistent='true',
                        )
                    )

        ctx.obj.broker.disconnect()
    else:
        raise RuntimeError(f'STOMP connection failed for {ctx.obj.broker}')


def get_routing_headers(plastron_context: PlastronContext, index_key: str):
    all_routing_headers = plastron_context.config['ROUTING_HEADERS']
    try:
        return all_routing_headers[index_key]
    except KeyError as e:
        raise RuntimeError(
            f'"{e}" is not a recognized index routing name. Use one of: {", ".join(all_routing_headers.keys())}'
        ) from e
