import logging
from collections.abc import Generator, Iterable
from typing import Any

import click

from plastron.cli import argument, option
from plastron.cli.utils import clean_lines
from plastron.jobs.exportjob import ExportJob
from plastron.serializers import SERIALIZER_CLASSES

logger = logging.getLogger(__name__)


@click.command(help='Export resources from the repository as a BagIt bag')
@click.option(
    '-o',
    '--output-dest',
    required=True,
    metavar='PATH|URI',
    help='Where to send the export. Can be a local filename or an SFTP URI.',
)
@click.option(
    '-t',
    '--export-format',
    type=click.Choice(SERIALIZER_CLASSES.keys()),
    required=True,
    help='Format for exported metadata',
)
@click.option(
    '--key',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, allow_dash=False),
    help='SSH private key file to use for SFTP connections.',
)
@click.option('--uri-template', metavar='URI_TEMPLATE', help='Public URI template.')
@click.option('-B', '--export-binaries', is_flag=True, help='Export binaries in addition to the metadata.')
@click.option(
    '--binary-types',
    metavar='MIME_TYPE[,MIME_TYPE...]',
    help='Include only binaries with a MIME type from this list.',
)
@option.uris_file(help='File containing a list of URIs of resources to export.')
@argument.uris(help='URIs of resources to export.')
@click.help_option('-h', '--help')
@click.pass_context
def export_command(
    ctx: click.Context,
    output_dest: str,
    key: str | None,
    export_format: str,
    uri_template: str | None,
    export_binaries: bool,
    binary_types: str | None,
    uris_file: Iterable[str] | None,
    uris: list[str],
):
    export_job = ExportJob(
        context=ctx.obj,
        export_binaries=export_binaries,
        binary_types=binary_types,
        uris=list(clean_lines(uris_file or [], uris)),
        export_format=export_format,
        output_dest=output_dest,
        uri_template=uri_template,
        key=key,
    )
    run(export_job.run())


def run(proc: Generator[dict[str, Any], None, dict[str, Any]]) -> dict[str, Any]:
    result = yield from proc
    return result
