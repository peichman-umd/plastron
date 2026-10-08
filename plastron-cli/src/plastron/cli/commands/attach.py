import logging

import click

from plastron.cli import option
from plastron.files import USAGE_TAGS, LocalFileSource
from plastron.repo import Repository, RepositoryError
from plastron.repo.pcdm import PCDMFileBearingResource

logger = logging.getLogger(__name__)


@click.command(help='Attach a binary to a resource in the repository')
@option.binary_filename(help='Local path to the binary file.')
@click.option(
    '--mime-type',
    metavar='MIME_TYPE',
    help='Use this MIME type instead of auto-detecting based on the BINARY_FILE.',
)
@click.option(
    '--slug',
    help='Use this as the resource slug instead of a randomly generated string.',
)
@click.option(
    '--usage',
    type=click.Choice(USAGE_TAGS.keys()),
    help='The purpose of this binary.',
)
@click.argument(
    'location',
    metavar='URI|PATH',
    help='The URI or repository path of the resource to attach the BINARY_FILE to.',
)
@click.help_option('--help', '-h')
@click.pass_context
def attach_command(
    ctx: click.Context,
    location: str,
    binary_filename: str,
    slug: str | None,
    mime_type: str | None,
    usage: str | None,
):
    repo: Repository = ctx.obj.repo
    try:
        resource = repo.get_resource(location, PCDMFileBearingResource).read()
    except RepositoryError as e:
        raise RuntimeError(str(e)) from e

    if not resource.exists:
        raise RuntimeError(f'Resource {resource.url} not found')

    source = LocalFileSource(binary_filename)

    try:
        with repo.transaction():
            file_resource = resource.create_file(
                source=source,
                slug=slug,
                rdf_types=USAGE_TAGS.get(usage, None),
                mime_type=mime_type,
            )

        click.echo(file_resource.url)

    except RepositoryError as e:
        raise RuntimeError(str(e)) from e
