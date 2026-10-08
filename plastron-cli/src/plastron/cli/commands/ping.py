import click
from requests.exceptions import ConnectionError


@click.command(help='Check connection to the repository')
@click.help_option('--help', '-h')
@click.pass_context
def ping_command(ctx: click.Context):
    try:
        ctx.obj.client.test_connection()
    except ConnectionError as e:
        raise RuntimeError(str(e)) from e
