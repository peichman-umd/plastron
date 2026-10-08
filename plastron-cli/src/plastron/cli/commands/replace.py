import logging

import click
from rdflib import Literal

from plastron.cli import option
from plastron.files import BinaryResource, LocalFileSource
from plastron.models.pcdm import PCDMFile
from plastron.repo import Repository, RepositoryError

logger = logging.getLogger(__name__)


@click.command(help='Replace a binary resource in the repository')
@option.binary_filename(help='Local path to the binary file.')
@click.option(
    '--mime-type',
    help='Use this MIME type instead of auto-detecting based on the BINARY_FILE.',
)
@click.argument(
    'location',
    help='URI or repository path of the resource to replace.',
    metavar='URI|PATH',
)
@click.help_option('--help', '-h')
@click.pass_context
def replace_command(
    ctx: click.Context,
    location: str,
    binary_filename: str,
    mime_type: str | None,
):
    repo: Repository = ctx.obj.repo
    try:
        resource = repo.get_resource(location, BinaryResource).read()
    except RepositoryError as e:
        raise RuntimeError(str(e)) from e

    if not resource.exists:
        raise RuntimeError(f'Resource {resource.url} not found')

    source = LocalFileSource(binary_filename)

    try:
        with repo.transaction():
            resource.update_binary(source, mime_type=mime_type)
            logger.info(f'Updating metadata for {resource.url}')
            file = resource.describe(PCDMFile)
            file.title = Literal(source.filename)
            resource.update()

        print(resource.url)

    except RepositoryError as e:
        raise RuntimeError(str(e)) from e
