import logging
from pathlib import Path

import click
from rdflib import Graph, Literal, URIRef

from plastron.cli import option
from plastron.cli.utils import parse_data_property, parse_object_property
from plastron.namespaces import dcterms, get_manager, pcdm, rdf
from plastron.utils import uri_or_curie

logger = logging.getLogger(__name__)

manager = get_manager()


@click.command(help='Create a resource in the repository')
@option.data_properties(
    help='An RDF data property to set on the newly created resource; VALUE is treated as a Literal; repeatable.'
)
@option.object_properties(
    help='An RDF object property to set on the newly created resource; VALUE is treated as a CURIE or URIRef; repeatable.'
)
@option.types(
    help='RDF type to add to the newly created resource; equivalent to "-O rdf:type TYPE"; TYPE is treated as a CURIE or URIRef; repeatable.'
)
@click.option(
    '--collection',
    'collection_name',
    help='Shortcut for "-T pcdm:collection -D dcterms:title NAME".',
    metavar='NAME',
)
@click.option(
    '--archival-group',
    help='Create this resource as an Archival Group (Fedora 6+ only).',
    is_flag=True,
)
@click.option(
    '--container',
    help='Parent container for the new resource; use this to create a new resource with a repository-generated identifier.',
    metavar='PATH',
)
@click.argument('path', help='Path to the new resource.', required=False)
@click.help_option('--help', '-h')
@click.pass_context
def create_command(
    ctx: click.Context,
    data_properties: list[tuple[str, str]],
    object_properties: list[tuple[str, str]],
    types: list[str],
    collection_name: str | None,
    archival_group: bool,
    container: str | None,
    path: str | None,
):
    properties: list[tuple[URIRef, Literal | URIRef]] = [
        *(parse_data_property(p, o) for p, o in data_properties),
        *(parse_object_property(p, o) for p, o in object_properties),
    ]

    if collection_name is not None:
        properties.append((rdf.type, pcdm.Collection))
        properties.append((dcterms.title, Literal(collection_name)))

    for rdf_type in types:
        properties.append((rdf.type, uri_or_curie(rdf_type)))

    graph = Graph(namespace_manager=manager)
    for p, o in properties:
        graph.add((URIRef(''), p, o))

    if path is not None:
        ctx.obj.client.create_at_path(Path(path), graph, archival_group=archival_group)
    elif container is not None:
        ctx.obj.client.create_in_container(Path(container), graph, archival_group=archival_group)
