import logging
from collections import defaultdict
from collections.abc import Iterable

import click
from rdflib import Literal

from plastron.cli import argument, option
from plastron.cli.utils import clean_lines
from plastron.models import get_model_from_name
from plastron.rdfmapping.descriptors import DataProperty, ObjectProperty
from plastron.rdfmapping.resources import RDFResourceBase
from plastron.repo import RepositoryResource
from plastron.utils import uri_or_curie

logger = logging.getLogger(__name__)


@click.command(help='Set property values on objects')
@click.option(
    '-m',
    '--model',
    'model_name',
    required=True,
    help='Name of the model class of the objects.',
)
@click.option(
    '-F',
    '--field',
    'fields_to_set',
    multiple=True,
    type=(str, str),
    metavar='FIELD_NAME VALUE',
    help='Field to set; repeatable; for object properties, VALUE should be either an absolute http:// or https:// URI, or a CURIE with a known prefix.',
)
@option.uris_file(help='File listing URIs of objects modify')
@argument.uris()
@click.help_option('--help', '-h')
@click.pass_context
def set_command(
    ctx: click.Context,
    model_name: str,
    fields_to_set: list[tuple[str, str]],
    uris_file: Iterable[str] | None,
    uris: list[str],
):
    model_class = get_model_from_name(model_name)
    values = get_new_values(model_class, fields_to_set)
    for uri in clean_lines(uris_file or [], uris):
        resource: RepositoryResource = ctx.obj.repo[uri].read()
        obj = resource.describe(model_class)
        for field, new_values in values.items():
            prop = getattr(obj, field)
            prop.update(new_values)
        validation = obj.validate()
        if validation.ok:
            logger.info(f'Resource {uri} is a valid {model_name}')
            resource.update()
            print(obj.uri)
        else:
            for field, error in validation.failures():
                logger.error(f'The value "{error.prop}" for field "{field}" {error}')
            logger.warning(f'Resource {uri} is invalid, skipping')


def get_new_values(model_class: type[RDFResourceBase], fields_to_set: Iterable[tuple[str, str]]) -> dict[str, set]:
    values = defaultdict(set)
    for field_name, value in fields_to_set:
        prop = getattr(model_class, field_name)
        if isinstance(prop, DataProperty):
            values[field_name].add(Literal(value, datatype=prop.datatype))
        elif isinstance(prop, ObjectProperty):
            values[field_name].add(uri_or_curie(value))
    return values
