import io
import logging
from collections.abc import Generator, Iterable
from typing import Any, TextIO

import click

from plastron.cli import option, argument
from plastron.cli.utils import clean_lines
from plastron.jobs import ItemLog
from plastron.jobs.updatejob import UpdateJob
from plastron.models import get_model_from_name
from plastron.utils import parse_predicate_list

logger = logging.getLogger(__name__)


@click.command(help='Update objects in the repository')
@click.option(
    '-u',
    '--update-file',
    help='Path to SPARQL Update file to apply',
    type=click.File(mode='r'),
    required=True,
)
@option.recursive()
@option.dry_run()
@click.option(
    '--transactions/--no-transactions',
    '--txn/--no-txn',
    'use_transactions',
    help='Run with or without using transactions.',
)
@click.option('--validate', is_flag=True, help='Validate before updating.')
@click.option(
    '-m',
    '--model',
    help='The model class to use for validation (Item, Issue, Poster, or Letter).',
)
@click.option('--completed', help='File recording the URIs of updated resources.')
@option.uris_file(help='File containing a list of URIs to update')
@argument.uris(help='URIs of repository objects to update')
@click.help_option('-h', '--help')
@click.pass_context
def update_command(
    ctx: click.Context,
    update_file: TextIO,
    recursive: str | None,
    dry_run: bool,
    use_transactions: bool,
    validate: bool,
    model: str | None,
    completed: str,
    uris_file: Iterable[str] | None,
    uris: list[str],
):
    if validate and model is None:
        raise RuntimeError('Model must be provided when performing validation')

    ctx.obj.client.test_connection()

    # Retrieve the model to use for validation
    model_class = get_model_from_name(model) if model else None

    sparql_update = update_file.read().encode('utf-8')

    if dry_run:
        logger.info('Dry run enabled, no actual updates will take place')

    if completed and not dry_run:
        completed_log = ItemLog(completed, ['uri', 'title', 'timestamp'], 'uri')
    else:
        completed_log = None

    traverse = parse_predicate_list(recursive) if recursive is not None else []

    update_job = UpdateJob(
        repo=ctx.obj.repo,
        uris=list(clean_lines(uris_file or [], uris)),
        sparql_update=sparql_update,
        model_class=model_class,
        traverse=traverse,
        completed=completed_log,
        dry_run=dry_run,
        use_transactions=use_transactions,
    )
    run(update_job.run())


def run(proc: Generator[dict[str, Any], None, dict[str, Any]]) -> dict[str, Any]:
    result = yield from proc
    return result
