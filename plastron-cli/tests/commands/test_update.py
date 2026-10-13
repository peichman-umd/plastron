from plastron.cli import plastron_command


def test_validate_requires_model(cli_runner, config_file_name, datadir):
    result = cli_runner.invoke(
        plastron_command,
        ['-c', config_file_name, 'update', '-u', str(datadir / 'empty.sparql'), '--validate'],
    )
    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert 'Model must be provided when performing validation' in str(result.exception)
