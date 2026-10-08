import importlib.metadata
import logging
import logging.config
import sys
from argparse import Namespace
from collections.abc import Iterable
from datetime import datetime, timezone
from importlib import import_module
from pkgutil import iter_modules
from typing import Any, cast

import click
import yaml
from plastron.cli import commands
from plastron.context import PlastronContext
from plastron.utils import (
    DEFAULT_LOGGING_OPTIONS,
    check_python_version,
    envsubst,
    uri_or_curie,
)
from rdflib import Literal, URIRef
from rdflib.util import from_n3

logger = logging.getLogger(__name__)
now = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
version = importlib.metadata.version('plastron-cli')


def load_commands(subparsers):
    # load all defined subcommands from the plastron.commands package, using
    # introspection
    command_modules = {}
    for finder, name, ispkg in iter_modules(commands.__path__):
        module_name = name
        if module_name == 'importcommand':
            # Special case handling for "importcommand", because "import" is
            # a Python reserved word that is not usable as a module name,
            # while we want "import" to be the Plastron command
            name = 'import'

        module = import_module(commands.__name__ + '.' + module_name)
        if hasattr(module, 'configure_cli'):
            module.configure_cli(subparsers)
            command_modules[name] = module
    return command_modules


def get_uris(args: Namespace) -> Iterable[str]:
    if hasattr(args, 'uris_file') or hasattr(args, 'uris'):
        if hasattr(args, 'uris_file') and args.uris_file is not None:
            yield from (line.rstrip() for line in args.uris_file)
        if hasattr(args, 'uris') and args.uris is not None:
            yield from args.uris
    else:
        # fall back to STDIN
        yield from (line.rstrip() for line in sys.stdin)


class LazyGroup(click.Group):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        try:
            return self.main(*args, **kwargs)
        except RuntimeError as e:
            logger.error(str(e))
            raise SystemExit(1)

    def list_commands(self, ctx):
        base = super().list_commands(ctx)
        return base + [ep.name for ep in importlib.metadata.entry_points(group='plastron_commands')]

    def get_command(self, ctx, cmd_name):
        try:
            entrypoint = importlib.metadata.entry_points(group='plastron_commands', name=cmd_name)[0]
            return entrypoint.load()
        except IndexError:
            return super().get_command(ctx, cmd_name)


@click.group(cls=LazyGroup, help='CLI tool for working with a Fedora repository', name='plastron')
@click.help_option('--help', '-h')
@click.version_option(version, '--version', '-V')
@click.option('-c', '--config', 'config_file', type=click.File(mode='r'), help='Path to configuration file.')
@click.option('-v', '--verbose', is_flag=True, help='Increase the verbosity of the status output.')
@click.option('-q', '--quiet', is_flag=True, help='Decrease the verbosity of the status output.')
@click.option(
    '--on-behalf-of', 'delegated_user', help='Delegate repository operations to this username.', metavar='USERNAME'
)
@click.pass_context
def main(ctx: click.Context, config_file, verbose, quiet, delegated_user):
    config = cast(dict[str, Any], envsubst(yaml.safe_load(config_file)))
    plastron_context = PlastronContext(config=config, delegated_user=delegated_user)
    ctx.obj = plastron_context
    logging_options = DEFAULT_LOGGING_OPTIONS

    """
    # TODO: put these into their own "LOGGING" config section
    # get basic logging options
    if 'LOGGING_CONFIG' in repo_config:
        with open(repo_config.get('LOGGING_CONFIG'), 'r') as logging_config_file:
            logging_options = yaml.safe_load(logging_config_file)
    else:
        logging_options = DEFAULT_LOGGING_OPTIONS

    # log file configuration
    log_dirname = repo_config.get('LOG_DIR')
    if not os.path.isdir(log_dirname):
        os.makedirs(log_dirname)
    log_filename = f'plastron.{args.cmd_name}.{now}.log'
    logfile = os.path.join(log_dirname, log_filename)
    logging_options['handlers']['file']['filename'] = logfile
    """

    # manipulate console verbosity
    if verbose:
        logging_options['handlers']['console']['level'] = 'DEBUG'
    elif quiet:
        logging_options['handlers']['console']['level'] = 'WARNING'
    else:
        logging_options['handlers']['console']['level'] = 'INFO'

    # configure logging
    logging.config.dictConfig(logging_options)

    check_python_version()

    plastron_context.client.ua_string = f'plastron/{plastron_context.version} ({ctx.invoked_subcommand})'
    logger.debug(f'Client User-Agent set to "{plastron_context.client.ua_string}"')
    logger.info(f'Loaded repo configuration from {config_file.name}')
    if delegated_user is not None:
        logger.info(f'Running repository operations on behalf of {delegated_user}')

    @ctx.call_on_close
    def footer():
        if not quiet:
            logger.info('Script complete. Goodbye!')

    # at this point, main delegates to the subcommand automatically


"""
def main():
    # Parse args and handle options.

    parser = ArgumentParser(prog='plastron', description='Batch operation tool for Fedora 4.')
    parser.set_defaults(cmd_name=None)

    common_required = parser.add_mutually_exclusive_group(required=True)
    common_required.add_argument(
        '-c', '--config', help='Path to configuration file.', action='store', dest='config_file', type=FileType('r')
    )
    common_required.add_argument('-V', '--version', help='Print version and exit.', action='version', version=version)

    parser.add_argument('-v', '--verbose', help='increase the verbosity of the status output', action='store_true')
    parser.add_argument('-q', '--quiet', help='decrease the verbosity of the status output', action='store_true')
    parser.add_argument(
        '--on-behalf-of', help='delegate repository operations to this username', dest='delegated_user', action='store'
    )

    parser.add_argument(
        '--batch-mode',
        '-b',
        help='specifies the use of batch user for interaction with fcrepo',
        dest='batch_mode',
        action='store',
        default=False,
    )

    subparsers = parser.add_subparsers(title='commands')

    command_modules = load_commands(subparsers)

    # parse command line args
    args = parser.parse_args()

    # if no subcommand was selected, display the help
    if args.cmd_name is None:
        parser.print_help()
        sys.exit(0)

    # new-style, combined config file (a la plastron.daemon)
    config = envsubst(yaml.safe_load(args.config_file))
    plastron_context = PlastronContext(config=config, args=args)
    repo_config: dict = config['REPOSITORY']

    # TODO: put these into their own "LOGGING" config section
    # get basic logging options
    if 'LOGGING_CONFIG' in repo_config:
        with open(repo_config.get('LOGGING_CONFIG'), 'r') as logging_config_file:
            logging_options = yaml.safe_load(logging_config_file)
    else:
        logging_options = DEFAULT_LOGGING_OPTIONS

    # log file configuration
    log_dirname = repo_config.get('LOG_DIR')
    if not os.path.isdir(log_dirname):
        os.makedirs(log_dirname)
    log_filename = f'plastron.{args.cmd_name}.{now}.log'
    logfile = os.path.join(log_dirname, log_filename)
    logging_options['handlers']['file']['filename'] = logfile

    # manipulate console verbosity
    if args.verbose:
        logging_options['handlers']['console']['level'] = 'DEBUG'
    elif args.quiet:
        logging_options['handlers']['console']['level'] = 'WARNING'

    # configure logging
    logging.config.dictConfig(logging_options)

    check_python_version()

    # get the selected subcommand
    command_module = command_modules[args.cmd_name]

    # dispatch to the selected subcommand
    try:
        if not hasattr(command_module, 'Command'):
            raise RuntimeError(f'Unable to execute command {args.cmd_name}')

        plastron_context.client.ua_string = f'plastron/{plastron_context.version} ({args.cmd_name})'
        logger.debug(f'Client User-Agent set to "{plastron_context.client.ua_string}"')

        command = command_module.Command(context=plastron_context)

        print_header(args)
        logger.info(f'Loaded repo configuration from {args.config_file.name}')
        if args.delegated_user is not None:
            logger.info(f'Running repository operations on behalf of {args.delegated_user}')
        command(args)
        print_footer(args)
    except RuntimeError as e:
        # something failed, exit with non-zero status
        logger.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        # aborted due to Ctrl+C
        sys.exit(2)
"""


def print_header(args):
    """Common header formatting."""
    if not args.quiet:
        title = '|     PLASTRON     |'
        bar = '+' + '=' * (len(title) - 2) + '+'
        spacer = '|' + ' ' * (len(title) - 2) + '|'
        print(f'\n{bar}\n{spacer}\n{title}\n{spacer}\n{bar}\n', file=sys.stderr)


def print_footer(args):
    """Report success or failure and resources created."""
    if not args.quiet:
        print('\nScript complete. Goodbye!\n', file=sys.stderr)


class ConfigError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def parse_data_property(p: str, o: str) -> tuple[URIRef, Literal]:
    """Convert a pair of strings to a URIRef predicate and Literal object."""
    return uri_or_curie(p), Literal(from_n3(o))


def parse_object_property(p: str, o: str) -> tuple[URIRef, URIRef]:
    """Convert a pair of strings to a URIRef predicate and URIRef object."""
    return uri_or_curie(p), uri_or_curie(o)
