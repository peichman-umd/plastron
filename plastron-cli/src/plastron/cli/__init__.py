#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib.metadata
import logging
import logging.config
import os
import sys
from argparse import ArgumentParser, FileType
from datetime import datetime
from importlib import import_module
from pkgutil import iter_modules

import pysolr
import yaml

from plastron.cli import commands
from plastron.client import Endpoint, Client, RepositoryStructure
from plastron.client.auth import get_authenticator
from plastron.utils import DEFAULT_LOGGING_OPTIONS, envsubst
from plastron.stomp.broker import Broker

logger = logging.getLogger(__name__)
now = datetime.utcnow().strftime('%Y%m%d%H%M%S')
version = importlib.metadata.version('plastron-cli')


def load_commands(subparsers):
    # load all defined subcommands from the plastron.commands package, using
    # introspection
    command_modules = {}
    for finder, name, ispkg in iter_modules(commands.__path__):
        module_name = name
        if module_name == "importcommand":
            # Special case handling for "importcommand", because "import" is
            # a Python reserved word that is not usable as a module name,
            # while we want "import" to be the Plastron command
            name = "import"

        module = import_module(commands.__name__ + '.' + module_name)
        if hasattr(module, 'configure_cli'):
            module.configure_cli(subparsers)
            command_modules[name] = module
    return command_modules


def main():
    """Parse args and handle options."""

    parser = ArgumentParser(
        prog='plastron',
        description='Batch operation tool for Fedora 4.'
    )
    parser.set_defaults(cmd_name=None)

    common_required = parser.add_mutually_exclusive_group(required=True)
    common_required.add_argument(
        '-r', '--repo',
        help='Path to repository configuration file.',
        action='store'
    )
    common_required.add_argument(
        '-c', '--config',
        help='Path to configuration file.',
        action='store',
        dest='config_file',
        type=FileType('r')
    )
    common_required.add_argument(
        '-V', '--version',
        help='Print version and exit.',
        action='version',
        version=version
    )

    parser.add_argument(
        '-v', '--verbose',
        help='increase the verbosity of the status output',
        action='store_true'
    )
    parser.add_argument(
        '-q', '--quiet',
        help='decrease the verbosity of the status output',
        action='store_true'
    )
    parser.add_argument(
        '--on-behalf-of',
        help='delegate repository operations to this username',
        dest='delegated_user',
        action='store'
    )

    parser.add_argument(
        '--batch-mode', '-b',
        help='specifies the use of batch user for interaction with fcrepo',
        dest='batch_mode',
        action='store',
        default=False
    )

    subparsers = parser.add_subparsers(title='commands')

    command_modules = load_commands(subparsers)

    # parse command line args
    args = parser.parse_args()

    # if no subcommand was selected, display the help
    if args.cmd_name is None:
        parser.print_help()
        sys.exit(0)

    if args.config_file is not None:
        # new-style, combined config file (a la plastron.daemon)
        config = envsubst(yaml.safe_load(args.config_file))
        repo_config = config['REPOSITORY']
        broker_config = config.get('MESSAGE_BROKER', None)
        command_config = config.get('COMMANDS') or {}
    else:
        # old-style, repository-only config file
        with open(args.repo, 'r') as repo_config_file:
            repo_config = yaml.safe_load(repo_config_file)
        broker_config = None
        command_config = {}

    try:
        repo = Endpoint(
            url=repo_config['REST_ENDPOINT'],
            default_path=repo_config.get('RELPATH', '/'),
            external_url=repo_config.get('REPO_EXTERNAL_URL'),
        )
        # TODO: respect the batch mode flag when getting the authenticator
        client = Client(
            endpoint=repo,
            auth=get_authenticator(repo_config),
            ua_string=f'plastron/{version}',
            on_behalf_of=args.delegated_user,
            structure=RepositoryStructure[repo_config.get('STRUCTURE', 'flat').upper()]
        )
    except ConfigError as e:
        logger.error(str(e))
        sys.exit(1)

    if broker_config is not None:
        broker = Broker(broker_config)
    else:
        broker = None

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
    log_filename = 'plastron.{0}.{1}.log'.format(args.cmd_name, now)
    logfile = os.path.join(log_dirname, log_filename)
    logging_options['handlers']['file']['filename'] = logfile

    # manipulate console verbosity
    if args.verbose:
        logging_options['handlers']['console']['level'] = 'DEBUG'
    elif args.quiet:
        logging_options['handlers']['console']['level'] = 'WARNING'

    # configure logging
    logging.config.dictConfig(logging_options)

    # get the selected subcommand
    command_module = command_modules[args.cmd_name]

    try:
        if not hasattr(command_module, 'Command'):
            raise RuntimeError(f'Unable to execute command {args.cmd_name}')

        command = command_module.Command(config=command_config.get(args.cmd_name.upper()))
        command.endpoint = client
        command.broker = broker

        # The SOLR configuration would only be necessary for the verify command, so it can be optional
        # Verify will check if solr got initialized and fail if it wasn't.
        if 'SOLR' in config and 'URL' in config['SOLR']:
            address = config['SOLR']['URL']
            command.solr = pysolr.Solr(address, always_commit=True, timeout=10)
        else:
            command.solr = None

        # dispatch to the selected subcommand
        print_header(args)
        logger.info(f'Loaded repo configuration from {args.repo or args.config_file.name}')
        if args.delegated_user is not None:
            logger.info(f'Running repository operations on behalf of {args.delegated_user}')
        command(client, args)
        print_footer(args)
    except RuntimeError as e:
        # something failed, exit with non-zero status
        logger.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        # aborted due to Ctrl+C
        sys.exit(2)


def print_header(args):
    """Common header formatting."""
    if not args.quiet:
        title = '|     PLASTRON     |'
        bar = '+' + '=' * (len(title) - 2) + '+'
        spacer = '|' + ' ' * (len(title) - 2) + '|'
        print('\n'.join(['', bar, spacer, title, spacer, bar, '']), file=sys.stderr)


def print_footer(args):
    """Report success or failure and resources created."""
    if not args.quiet:
        print('\nScript complete. Goodbye!\n', file=sys.stderr)


if __name__ == "__main__":
    main()


class ConfigError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
