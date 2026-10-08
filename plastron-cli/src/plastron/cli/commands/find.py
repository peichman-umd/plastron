import logging
from collections.abc import Callable, Iterable, Iterator

import click
from rdflib import Literal, URIRef

from plastron.cli import parse_data_property, parse_object_property, option, argument
from plastron.namespaces import get_manager, rdf
from plastron.repo import RepositoryResource
from plastron.utils import parse_predicate_list, uri_or_curie

logger = logging.getLogger(__name__)
manager = get_manager()


@click.command(help='Find objects in the repository')
@option.data_properties(help='An RDF data property to match; VALUE is treated as a Literal; repeatable.')
@option.object_properties(help='An RDF object property to match; VALUE is treated as a CURIE or URIRef; repeatable.')
@option.types(help='An RDF type to match; shorthand for "-O rdf:type TYPE"; repeatable.')
@click.option(
    '--match-all',
    is_flag=True,
    help='Require all properties to match to include a resource in the result list; this is the default behavior.',
)
@click.option(
    '--match-any', is_flag=True, help='Require at least one property to match to include a resource in the result list.'
)
@option.recursive()
@argument.uris(help='Search starting at this URI in the repository; repeatable. Defaults to the repository root ("/").')
@click.help_option('--help', '-h')
@click.pass_context
def find_command(
    ctx: click.Context,
    data_properties: list[tuple[str, str]],
    object_properties: list[tuple[str, str]],
    types: list[str],
    match_all: bool,
    match_any: bool,
    recursive: str | None,
    uris: list[str],
):
    properties: list[tuple[URIRef, Literal | URIRef]] = [
        *(parse_data_property(p, o) for p, o in data_properties),
        *(parse_object_property(p, o) for p, o in object_properties),
    ]

    for rdf_type in types:
        properties.append((rdf.type, uri_or_curie(rdf_type)))

    if match_any:
        match = any
    elif match_all:
        match = all
    else:
        match = all

    if len(properties) == 0:
        logger.info('Matching all resources')
    else:
        logger.info(f'Matching resources with {match.__name__} of these properties:')
        for p, o in properties:
            logger.info(f'  {p.n3(namespace_manager=manager)} {o.n3(namespace_manager=manager)}')

    resource_count = 0

    traverse = parse_predicate_list(recursive) if recursive else []

    if traverse:
        logger.info('Predicates used for recursive matching:')
        for p in traverse:
            logger.info(f'  {p.n3(namespace_manager=manager)}')

    # default to search the repo root
    for uri in uris or ['/']:
        for resource in find(
            start_resource=ctx.obj.repo[uri],
            matcher=match,
            traverse=traverse,
            properties=properties,
        ):
            resource_count += 1
            click.echo(resource.url)

    logger.info(f'Found {resource_count} resource(s)')


def find(
    start_resource: RepositoryResource,
    matcher: Callable[[Iterable], bool],
    traverse: list[URIRef] | None = None,
    properties: list[tuple] | None = None,
) -> Iterator[RepositoryResource]:
    if traverse is None:
        traverse = []
    if properties is None:
        properties = []
    for resource in start_resource.walk(traverse=traverse):
        if len(properties) > 0:
            subject = URIRef(resource.url)
            if matcher((subject, p, o) in resource.graph for p, o in properties):
                yield resource
        else:
            # with no filters specified, list all resources found
            # this mimics the behavior of the Linux "find" command
            yield resource
