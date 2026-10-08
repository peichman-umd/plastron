import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from itertools import chain

import click

from plastron.cli import argument, option
from plastron.client import ClientError
from plastron.jobs import ItemLog
from plastron.models.pcdm import PCDMObject
from plastron.repo import RepositoryError
from plastron.repo.utils import context
from plastron.utils import parse_predicate_list

logger = logging.getLogger(__name__)


@click.command(help='Delete objects from the repository')
@option.recursive()
@option.dry_run()
@click.option(
    '--transactions/--no-transactions',
    '--txn/--no-txn',
    'use_transactions',
    help='Run with or without using transactions.',
)
@click.option('--completed', help='File recording the URIs of deleted resources.', type=click.Path())
@option.uris_file(help='File containing a list of URIs of resources to delete.')
@argument.uris(help='Repository URIs to be deleted.')
@click.help_option('--help', '-h')
@click.pass_context
def delete_command(
    ctx: click.Context,
    recursive: str | None,
    dry_run: bool,
    use_transactions: bool,
    completed,
    uris_file: Iterable[str],
    uris: list[str],
):
    ctx.obj.client.test_connection()
    if completed:
        completed_log = ItemLog(completed, ['uri', 'title', 'timestamp'], 'uri')
    else:
        completed_log = None

    if dry_run:
        logger.info('Dry run enabled, no actual deletions will take place')

    if recursive:
        traverse = parse_predicate_list(recursive)
    else:
        # if recursive was not specified, traverse nothing
        traverse = []

    for uri in chain(uris_file or [], uris):
        with context(repo=ctx.obj.repo, use_transactions=use_transactions, dry_run=dry_run):
            try:
                for resource in ctx.obj.repo[uri].walk(traverse=traverse):
                    obj = resource.describe(PCDMObject)
                    title = obj.title
                    if dry_run:
                        logger.info(f'Would delete resource {resource.url} "{title}"')
                        continue
                    resource.delete()
                    if completed_log is not None:
                        completed_log.append(
                            {
                                'uri': resource.url,
                                'title': str(title),
                                'timestamp': datetime.now(timezone.utc).isoformat('T'),
                            }
                        )
            except RepositoryError as e:
                if isinstance(e.__cause__, ClientError) and e.__cause__.status_code in (404, 410):
                    # not a problem to try and delete something that is not there
                    logger.info(f'Resource {uri} does not exist; skipping')
                else:
                    raise
