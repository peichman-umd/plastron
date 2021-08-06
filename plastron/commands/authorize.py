from argparse import FileType
from pathlib import Path

from rdflib import Graph, URIRef

from plastron.commands import BaseCommand
from plastron.commands.create import create_at_path, parse_data_property, parse_object_property
from plastron.http import Repository, ResourceURI
from plastron.namespaces import acl, foaf, get_manager, rdf, webac
from plastron.util import ResourceList


manager = get_manager()

ACL_CONTAINER_PATH = Path('/acls')
ACL_GRAPH = Graph()
ACL_GRAPH.add((URIRef(''), rdf.type, webac.Acl))


def find_or_create_acl(repo: Repository, resource_path: Path):
    """
    Find or create an ACL at a path based on the resource's path.
    """

    # strip the leading '/' from the resource_path for it to
    # properly compose using the pathlib / operator
    acl_path = ACL_CONTAINER_PATH / resource_path[1:]
    if repo.path_exists(str(acl_path)):
        return ResourceURI(
            uri=repo.endpoint + str(acl_path),
            description_uri=repo.get_description_uri(repo.endpoint + str(acl_path))
        )
    else:
        return create_at_path(repo, acl_path, ACL_GRAPH)


def create_authorizations(repo: Repository, resource: ResourceURI, acl_resource: ResourceURI, name, agents, modes):
    authz_graph = Graph(namespace_manager=manager)
    authz_path = acl_resource.path(repo) / name
    authz_properties = [parse_object_property('acl:mode', o) for o in modes.split(',')]
    if agents == 'foaf:Agent':
        # special handling for foaf:Agent
        authz_properties.append([acl.agent, foaf.Agent])
    else:
        # otherwise, assume these are string usernames
        authz_properties.extend([parse_data_property('acl:agent', o) for o in agents.split(',')])
    authz_properties.append([rdf.type, acl.Authorization])
    authz_properties.append([acl.accessTo, URIRef(resource.uri)])
    for p, o in authz_properties:
        authz_graph.add((URIRef(''), p, o))
    # create the authorization
    return create_at_path(repo, authz_path, authz_graph)


def configure_cli(subparsers):
    parser = subparsers.add_parser(
        name='authorize',
        description='Manage resource access control lists (ACLs)'
    )
    parser.add_argument(
        '--add', '-a',
        nargs=3,
        dest='authorizations_to_add',
        action='append',
        metavar=('NAME', 'AGENTS', 'MODES'),
        default=[],
        help=(
            'add an authorization named NAME; AGENTS is a comma-separated '
            'list of string usernames (or the special string "foaf:Agent");'
            'MODES as a comma-separated list of WebAC access modes (acl:Read, '
            'acl:Write, etc.)'
        )
    )
    parser.add_argument(
        '--file', '-f',
        type=FileType('r', encoding='utf-8'),
        help=(
            'file containing a list of URIs to apply authorizations to; '
            'use "-" for STDIN'
        )
    )
    parser.add_argument(
        'uris', nargs='*',
        help='URIs of repository objects to apply authorizations to'
    )
    parser.set_defaults(cmd_name='authorize')


class Command(BaseCommand):
    def __call__(self, repo, args):
        self.authorizations_to_add = args.authorizations_to_add
        resources = ResourceList(
            repository=repo,
            uris=args.file or args.uris or []
        )
        resources.process(
            method=self.add_authorizations
        )

    def add_authorizations(self, resource, _graph, repo: Repository):
        if resource and len(self.authorizations_to_add) > 0:
            resource_path = repo.repo_path(resource.uri)

            acl_resource = find_or_create_acl(repo, resource_path)

            for name, agents, modes in self.authorizations_to_add:
                create_authorizations(repo, resource, acl_resource, name, agents, modes)

            # update the resource to point to the ACL
            linking_graph = Graph()
            linking_graph.add((URIRef(''), acl.accessControl, URIRef(acl_resource.uri)))
            repo.patch(
                resource.uri,
                data=repo.build_sparql_update(insert_graph=linking_graph),
                headers={'Content-Type': 'application/sparql-update'}
            )

            print(resource.uri)
