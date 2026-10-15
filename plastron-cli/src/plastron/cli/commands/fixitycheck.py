import csv
import json
import logging
import sys
from collections.abc import Callable

import click

from plastron.cli import argument, option
from plastron.cli.utils import clean_lines
from plastron.files import BinaryResource, FixityCheckingError
from plastron.models.fedora import FedoraBinary

logger = logging.getLogger(__name__)


@click.command(help='Run a fixity check on objects in the repository')
@click.option(
    '--format',
    '-t',
    'output_format',
    type=click.Choice(['csv', 'jsonl']),
    default='csv',
    help='output format of results; default is "csv"',
)
@option.uris_file(help='File containing a list of URIs of objects to fixity check')
@argument.uris(help='URIs of objects to fixity check')
@click.help_option('--help', '-h')
@click.pass_context
def fixitycheck_command(
    ctx: click.Context,
    output_format: str,
    uris_file,
    uris: list[str],
):
    write = get_writer(output_format)
    for uri in clean_lines(uris_file or [], uris):
        binary_resource = ctx.obj.repo.read(uri, BinaryResource)

        try:
            fixity_details = binary_resource.check_fixity()
        except FixityCheckingError as e:
            logger.error(f'Skipping {uri}: {e}')
            continue

        if fixity_details.is_success:
            logger.info(f'Fixity check of {uri} succeeded')
        else:
            logger.info(f'Fixity check of {uri} failed: {fixity_details.outcome}')

        obj = binary_resource.describe(FedoraBinary)
        result = {
            'uri': str(obj.uri),
            'outcome': ';'.join(fixity_details.outcome),
            'checksum': str(fixity_details.digest),
            'size': int(str(fixity_details.size)),
            'time': fixity_details.timestamp.isoformat(),
            'expected_checksum': str(obj.digest),
            'expected_size': int(str(obj.size)),
            'last_modified': str(obj.last_modified),
        }
        write(result)


def get_writer(output_format: str) -> Callable[[dict], None]:
    match output_format:
        case 'csv':
            writer = csv.writer(sys.stdout)
            return lambda result: writer.writerow(result.values())
        case 'jsonl':
            return lambda result: print(json.dumps(result))
        case _:
            raise RuntimeError(f'Unknown output format: {output_format}')
