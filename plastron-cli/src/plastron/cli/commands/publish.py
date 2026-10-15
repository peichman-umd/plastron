import logging
from collections.abc import Iterable

import click

from plastron.cli import argument, option
from plastron.cli.utils import clean_lines
from plastron.repo import RepositoryError
from plastron.repo.publish import PublishableResource

logger = logging.getLogger(__name__)


@click.command(help='Publish digital objects')
@click.option(
    '--hidden',
    'force_hidden',
    is_flag=True,
    help='Set the "Hidden" state on these objects.',
)
@click.option(
    '--visible',
    'force_visible',
    is_flag=True,
    help='Remove the "Hidden" state from these objects.',
)
@option.uris_file(help='File containing URIs of objects to publish.')
@argument.uris(help='URIs of objects to publish.')
@click.help_option('-h', '--help')
@click.pass_context
def publish_command(
    ctx: click.Context,
    force_hidden: bool,
    force_visible: bool,
    uris_file: Iterable[str] | None,
    uris: list[str],
):
    for uri in clean_lines(uris_file or [], uris):
        # get the resource and check for an existing handle and current publication status
        try:
            resource: PublishableResource = ctx.obj.repo[uri:PublishableResource].read()
        except RepositoryError as e:
            logger.error(f'Unable to retrieve {uri}: {e}')
            continue

        try:
            handle = resource.publish(
                handle_client=ctx.obj.handle_client,
                public_url=ctx.obj.get_public_url(resource),
                force_hidden=force_hidden,
                force_visible=force_visible,
            )
        except RepositoryError as e:
            logger.error(str(e))
            continue

        logger.info(f'Publication status of {uri} is {resource.publication_status}')
        logger.info(f'Handle for repo URI {uri} is {handle} ({handle.hdl_uri}) with target URL {handle.url}')
