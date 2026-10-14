import csv
import logging

import click

logger = logging.getLogger(__name__)


@click.command(help="Verify item URIs are indexed in Solr and display URIs that aren't")
@click.argument(
    'completed_log',
    type=click.File(mode='r'),
    help='completed log file from an import job',
)
@click.help_option('--help', '-h')
@click.pass_context
def verify_command(ctx: click.Context, completed_log):
    invalid_items = []
    reader = csv.DictReader(completed_log)

    for item in reader:
        query = ctx.obj.solr.search(f'id:"{item["uri"]}"')

        if len(query) == 0:
            invalid_items.append(item['uri'])

    if len(invalid_items) > 0:
        logger.info(f"There are {len(invalid_items)} items in {completed_log} whose URIs aren't indexed")
        for item in invalid_items:
            click.echo(item)
    else:
        logger.info('All URIs in the mapfile are indexed!')
