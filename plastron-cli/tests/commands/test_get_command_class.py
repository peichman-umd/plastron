import pytest

from plastron.cli.commands import BaseCommand, get_command_class


def test_get_command_class():
    cls = get_command_class('create')
    assert issubclass(cls, BaseCommand)


def test_get_import_command_class():
    # test the special case
    cls = get_command_class('import')
    assert issubclass(cls, BaseCommand)
    assert cls.__module__ == 'plastron.cli.commands.importcommand'


def test_non_existent_command_class():
    with pytest.raises(RuntimeError):
        _cls = get_command_class('foo')
