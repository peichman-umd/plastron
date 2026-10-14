import logging

import click
from PIL import Image

from plastron.cli import argument
from plastron.files import BinaryResource
from plastron.models.pcdm import PCDMImageFile
from plastron.repo.utils import context

Image.MAX_IMAGE_PIXELS = None

logger = logging.getLogger(__name__)


@click.command(help='Add width and height to image resources')
@argument.uris(help='URIs of repository objects to get image info')
def imgsize_command(ctx: click.Context, uris: list[str]):
    for uri in uris:
        file_resource: BinaryResource = ctx.obj.repo.read(uri, BinaryResource)
        file = file_resource.describe(PCDMImageFile)

        if file.mime_type.value.startswith('image/'):
            with context(repo=ctx.obj.repo):
                logger.info(f'Reading image data from {uri}')

                with file_resource.open() as file_contents:
                    image = Image.open(file_contents)

                logger.info(f'URI: {uri}, Width: {image.width}, Height: {image.height}')
                file.width = image.width
                file.height = image.height
                file_resource.update()

        else:
            logger.warning(f'{uri} is not of type image/*; skipping')
