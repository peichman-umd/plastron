from pathlib import Path

import pytest
import responses
from click.testing import Result
from responses import GET, HEAD, DELETE

from plastron.cli import plastron_command
from plastron.jobs import ItemLog


def is_success(result: Result) -> bool:
    return result.exit_code == 0


def is_not_success(result: Result) -> bool:
    return result.exit_code != 0


@pytest.mark.parametrize(
    ('path', 'response_args', 'expected'),
    [
        # resource exists, delete successful
        (
            '/ok',
            {
                HEAD: {'status': 200},
                GET: {'status': 200, 'adding_headers': {'Content-Type': 'application/n-triples'}, 'body': ''},
                DELETE: {'status': 204},
            },
            is_success,
        ),
        # resource not found
        (
            '/not_found',
            {
                HEAD: {'status': 404},
                GET: {'status': 404, 'body': ''},
                DELETE: {'status': 404},
            },
            is_success,
        ),
        # resource gone
        (
            '/gone',
            {
                HEAD: {'status': 410},
                GET: {'status': 410, 'body': ''},
                DELETE: {'status': 410},
            },
            is_success,
        ),
        # resource exists, internal server error while deleting
        (
            '/internal_server_error',
            {
                HEAD: {'status': 200},
                GET: {'status': 200, 'adding_headers': {'Content-Type': 'application/n-triples'}, 'body': ''},
                DELETE: {'status': 500},
            },
            is_not_success,
        ),
        # resource exists, bad request error while deleting
        (
            '/bad_request',
            {
                HEAD: {'status': 200},
                GET: {'status': 200, 'adding_headers': {'Content-Type': 'application/n-triples'}, 'body': ''},
                DELETE: {'status': 400},
            },
            is_not_success,
        ),
    ],
)
@responses.activate
def test_delete_command(
    cli_runner, config_file_name, repo, register_root, path, response_args, expected, register_resource
):
    register_root()
    register_resource(
        url=str(repo[path].url),
        response_args=response_args,
    )
    result = cli_runner.invoke(plastron_command, ['-c', config_file_name, 'delete', path])
    assert expected(result)


@responses.activate
def test_completed_log(cli_runner, config_file_name, datadir, repo, register_root, register_resource):
    register_root()
    deleted_url = str(repo['/test'].url)
    title_triple = f'<{deleted_url}> <http://purl.org/dc/terms/title> "Test Resource" .'
    register_resource(
        url=deleted_url,
        response_args={
            HEAD: {'status': 200},
            GET: {'status': 200, 'adding_headers': {'Content-Type': 'application/n-triples'}, 'body': title_triple},
            DELETE: {'status': 204},
        },
    )
    completed_log_path: Path = datadir / 'completed.csv'
    result = cli_runner.invoke(
        plastron_command, ['-c', config_file_name, 'delete', '/test', '--completed', str(completed_log_path)]
    )
    assert result.exit_code == 0
    assert completed_log_path.exists()
    completed_log = ItemLog(filename=completed_log_path, fieldnames=['uri', 'title', 'timestamp'], keyfield='uri')
    assert deleted_url in completed_log
    assert completed_log[0]['title'] == 'Test Resource'


# TODO: test dry-run
# TODO: test recursive
