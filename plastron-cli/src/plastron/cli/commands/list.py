import logging

import click

from plastron.cli import argument
from plastron.models.ldp import LDPContainer
from plastron.models.pcdm import PCDMObject
from plastron.repo import RepositoryError

logger = logging.getLogger(__name__)


@click.command(help='List objects in the repository')
@click.option('--long', '-l', is_flag=True, help='Display additional information besides the URI.')
@argument.uris(help='URIs of repository objects to list.')
@click.pass_context
def ls_command(ctx: click.Context, long: bool, uris: list[str]):
    # default to list the repo root
    for uri in uris or ['/']:
        resource = ctx.obj.repo.get_resource(uri)
        try:
            resource.read()
        except RepositoryError as e:
            logger.error(str(e))
            continue

        for child_uri in resource.describe(LDPContainer).contains:
            if long:
                child_obj = ctx.obj.repo.read(child_uri).describe(PCDMObject)
                click.echo(f'{child_uri} {child_obj.title}')
            else:
                click.echo(child_uri)
