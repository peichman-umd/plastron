import importlib.metadata
import logging
import logging.config
from pathlib import Path
from typing import Any, cast

import click
import yaml

from plastron.cli.utils import EntryPointsGroup
from plastron.context import PlastronContext
from plastron.utils import (
    DEFAULT_LOGGING_OPTIONS,
    check_python_version,
    envsubst,
    datetimestamp,
)

logger = logging.getLogger(__name__)
version = importlib.metadata.version('plastron-cli')


def configure_logging(
    logging_config: dict[str, Any],
    subcommand_name: str | None,
    verbose: bool = False,
    quiet: bool = False,
):
    logging_options = DEFAULT_LOGGING_OPTIONS
    # log file configuration
    log_dirname: str | None = logging_config.get('DIR')
    if log_dirname is not None:
        log_dir = Path(log_dirname)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f'plastron.{subcommand_name or ""}.{datetimestamp()}.log'
        logging_options['handlers']['file'] = {
            'class': 'logging.FileHandler',
            'filename': str(log_file),
            'level': logging_config.get('LEVEL', 'DEBUG'),
            'formatter': 'full',
        }
        for logger_name in ('__main__', 'plastron'):
            logging_options['loggers'][logger_name]['handlers'].append('file')

    # manipulate console verbosity
    if verbose:
        logging_options['handlers']['console']['level'] = 'DEBUG'
    elif quiet:
        logging_options['handlers']['console']['level'] = 'WARNING'
    else:
        logging_options['handlers']['console']['level'] = 'INFO'

    logging.config.dictConfig(logging_options)


@click.group(
    cls=EntryPointsGroup,
    help='CLI tool for working with a Fedora repository',
    name='plastron',
    entry_points_group='plastron_commands',
)
@click.help_option('--help', '-h')
@click.version_option(version, '--version', '-V')
@click.option('-c', '--config', 'config_file', type=click.File(mode='r'), help='Path to configuration file.')
@click.option('-v', '--verbose', is_flag=True, help='Increase the verbosity of the status output.')
@click.option('-q', '--quiet', is_flag=True, help='Decrease the verbosity of the status output.')
@click.option(
    '--on-behalf-of', 'delegated_user', help='Delegate repository operations to this username.', metavar='USERNAME'
)
@click.pass_context
def plastron_command(ctx: click.Context, config_file, verbose: bool, quiet: bool, delegated_user: str | None):
    config = cast(dict[str, Any], envsubst(yaml.safe_load(config_file)))
    plastron_context = PlastronContext(config=config, delegated_user=delegated_user)
    ctx.obj = plastron_context

    configure_logging(config.get('LOGGING', {}), ctx.invoked_subcommand, verbose=verbose, quiet=quiet)

    check_python_version()

    if not quiet:
        title = '|     PLASTRON     |'
        bar = '+' + '=' * (len(title) - 2) + '+'
        spacer = '|' + ' ' * (len(title) - 2) + '|'
        logger.info(f'\n{bar}\n{spacer}\n{title}\n{spacer}\n{bar}\n')

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


class ConfigError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
