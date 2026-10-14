import csv
import logging
from collections.abc import Iterable

import click
from rdflib import URIRef

from plastron.client import ClientError
from plastron.files import BinarySource, HTTPFileSource, LocalFileSource
from plastron.models.umd import Stub
from plastron.repo import ContainerResource
from plastron.repo.pcdm import PCDMFileBearingResource
from plastron.repo.utils import context
from plastron.utils import uri_or_curie

logger = logging.getLogger(__name__)


def get_source(binary_column_value: str) -> BinarySource | None:
    """
    Returns the appropriate BinarySource implementation to use, based on the
    value in the binary column, or None if an appropriate BinarySource
    implementation cannot be determined.
    """
    source: BinarySource | None = None
    if binary_column_value.startswith(('http:', 'https:')):
        source = HTTPFileSource(binary_column_value)
    elif binary_column_value is not None:
        source = LocalFileSource(binary_column_value)
    return source


def write_csv_header(
    fieldnames: Iterable[str],
    csv_writer: csv.DictWriter,
    renaming: list[tuple[str | None, str | None]] | None = None,
):
    """
    Writes the CSV header line to the output, possibly replacing the
    binary_column header with a renamed header.

    This is needed because the binary_column in the output will always
    be a URL, while the binary_column in the input may be a filepath
    (and thus have a column name that is not descriptive of the output).
    """
    if fieldnames is not None:
        csv_header_dict = dict(zip(fieldnames, fieldnames))
        if renaming is not None:
            for old, new in renaming:
                if old is not None and new is not None:
                    csv_header_dict[old] = new
        csv_writer.writerow(csv_header_dict)


@click.command(help='create stub resources with just an identifier and binary')
@click.option(
    '--identifier-column',
    help='column in the source CSV file with a unique identifier for each item',
    required=True,
)
@click.option(
    '--binary-column',
    help=(
        'column in the source CSV file with the location of the binary to '
        'load. Supports http: and https: (must begin with "http:" or '
        '"https:"), and file resources (relative or absolute file path). '
        'Relative file paths are relative to where the command is run.'
    ),
    required=True,
)
@click.option(
    '--rename-binary-column',
    'new_binary_column_name',
    help='Renames the binary column in the CSV output to the provided name.',
)
@click.option('--member-of', help='URI of the object that new items are PCDM members of')
@click.option('--access', help='URI or CURIE of the access class to apply to new items', type=uri_or_curie)
@click.option(
    '--container',
    'container_path',
    help='Parent container for new items',
)
@click.option(
    '-o',
    '--output-file',
    help=(
        'destination for a copy of the source CSV file '
        'with the binary-column value replaced with the '
        'newly created repository URI for the binary; '
        'defaults to STDOUT if not given'
    ),
)
@click.argument(
    'source_file',
    help='Name of the CSV file to create stubs from; use "-" to read from STDIN.',
    type=click.File(mode='r'),
)
@click.help_option('-h', '--help')
@click.pass_context
def stub_command(
    ctx: click.Context,
    identifier_column: str,
    binary_column: str,
    new_binary_column_name: str,
    member_of: str,
    access: str,
    container_path: str,
    output_file,
    source_file,
):
    csv_file = csv.DictReader(source_file)
    if csv_file.fieldnames is None:
        raise RuntimeError(f'No fields found in {csv_file}. Exiting.')

    csv_writer = csv.DictWriter(output_file, fieldnames=csv_file.fieldnames)

    write_csv_header(
        fieldnames=csv_file.fieldnames,
        csv_writer=csv_writer,
        renaming=[(binary_column, new_binary_column_name)],
    )
    container_path = container_path or ctx.obj.repo.endpoint.relpath
    container_resource: ContainerResource = ctx.obj.repo[container_path:ContainerResource].read()

    for _, row in enumerate(csv_file, start=1):
        identifier = row[identifier_column]
        source = get_source(row[binary_column])
        if not source:
            logger.warning(f'No source found for {identifier}; skipping')
            csv_writer.writerow(row)
            continue

        item = Stub(title=f'Stub for {identifier}', identifier=identifier)

        if member_of is not None:
            item.member_of = URIRef(member_of)
        if access is not None:
            item.rdf_type.add(URIRef(access))

        with context(repo=ctx.obj.repo):
            try:
                access_types = [access] if access is not None else []

                resource = container_resource.create_child(resource_class=PCDMFileBearingResource, description=item)
                resource.create_file(source, rdf_types=access_types)

                row[binary_column] = resource.url
                csv_writer.writerow(row)
            except (ClientError, FileNotFoundError) as e:
                logger.error(f'{item.identifier} not created: {e}')
            else:
                logger.info(f'Created {resource.url}')
