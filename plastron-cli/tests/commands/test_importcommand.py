import os
import tempfile
from csv import DictReader
from uuid import uuid4

import pytest
import yaml

from plastron.cli import main
from plastron.jobs import JobConfigError, JobNotFoundError


def test_cannot_resume_without_job_id(runner, config_file_name):
    # Verifies that the import command throws RuntimeError when resuming a
    # job and the job id is not provided
    result = runner.invoke(main, ['-c', config_file_name, 'import', '--resume'])
    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert 'Resuming a job requires a job id' in str(result.exception)


def test_cannot_resume_without_job_directory(runner, datadir):
    # Verifies that the import command throws RuntimeError when resuming a
    # job and the directory associated with job id is not found
    result = runner.invoke(main, ['-c', datadir / 'nonexistent-jobs-dir/plastron.yml', 'import', '--resume', '--job-id', str(uuid4())])
    assert result.exit_code != 0
    assert isinstance(result.exception, JobNotFoundError)
    assert 'does not exist' in str(result.exception)


def test_cannot_resume_without_config_file(runner, datadir):
    # Verifies that the import command throws JobConfigError when resuming a
    # job and a config file is not found
    job_id = str(uuid4())
    with tempfile.TemporaryDirectory() as tmpdirname:
        with (datadir / 'no-job-config/plastron.yml').open(mode='w') as fh:
            yaml.dump({'REPOSITORY': {'REST_ENDPOINT': 'http://localhost:9999'}, 'COMMANDS': {'IMPORT': {'JOBS_DIR': tmpdirname}}}, stream=fh)

        # Make subdirectory in tmpdirname for job
        job_dir = os.path.join(tmpdirname, job_id)
        os.mkdir(job_dir)

        result = runner.invoke(main, ['-c', datadir / 'no-job-config/plastron.yml', 'import', '--resume', '--job-id', job_id])
        assert result.exit_code != 0
        assert isinstance(result.exception, JobConfigError)
        assert 'config.yml is missing' in str(result.exception)


def test_model_is_required_unless_resuming(runner, datadir, config_file_name):
    # Verifies that the import command throws RuntimeError if model
    # is not provided when not resuming
    result = runner.invoke(main, ['-c', config_file_name, 'import', '--container', 'test_container', str(datadir / 'import.csv')])
    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert 'A model is required unless resuming an existing job' in str(result.exception)


def test_import_file_is_required_unless_resuming(runner, config_file_name):
    # Verifies that the import command throws RuntimeError if an import_file
    # is not provided when not resuming
    result = runner.invoke(main, ['-c', config_file_name, 'import', '--container', 'test_container', '--model', 'Item'])
    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert 'An import file is required unless resuming an existing job' in str(result.exception)


def test_container_is_required_unless_resuming(runner, datadir, config_file_name):
    # Verifies that the import command throws RuntimeError if an import_file
    # is not provided when not resuming
    result = runner.invoke(main, ['-c', config_file_name, 'import', '--model', 'Item', str(datadir / 'import.csv')])
    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert 'A container is required unless resuming an existing job' in str(result.exception)


@pytest.mark.parametrize(
    ('model_name', 'expected_header_fields'),
    [
        (
            'Item',
            [
                'Object Type',
                'Identifier',
                'Rights Statement',
                'Title',
                'Format',
                'Archival Collection',
                'Presentation Set',
                'Date',
                'Description',
                'Alternate Title',
                'Creator',
                'Creator URI',
                'Contributor',
                'Contributor URI',
                'Publisher',
                'Publisher URI',
                'Audience',
                'Audience URI',
                'Location',
                'Extent',
                'Subject',
                'Language',
                'Rights Holder',
                'Terms of Use',
                'Copyright Notice',
                'Collection Information',
                'Accession Number',
                'Handle',
                'FILES',
                'ITEM_FILES',
            ],
        ),
        (
            'Letter',
            [
                'Title',
                'Rights Holder',
                'Extent',
                'Bibliographic Citation',
                'Description',
                'Language',
                'Date',
                'Resource Type',
                'Rights',
                'Terms of Use',
                'Copyright Notice',
                'Subject',
                'Location',
                'Longitude',
                'Latitude',
                'Archival Collection',
                'Handle/Link',
                'Identifier',
                'Recipient',
                'Author',
                'Handle',
                'Presentation Set',
                'FILES',
                'ITEM_FILES',
            ],
        ),
        (
            'Poster',
            [
                'Title',
                'Alternate Title',
                'Publisher',
                'Collection',
                'Format',
                'Resource Type',
                'Date',
                'Language',
                'Description',
                'Extent',
                'Issue',
                'Identifier/Call Number',
                'Location',
                'Longitude',
                'Latitude',
                'Subject',
                'Rights',
                'Terms of Use',
                'Copyright Notice',
                'Identifier',
                'Handle',
                'Presentation Set',
                'FILES',
                'ITEM_FILES',
            ],
        ),
        (
            'Issue',
            [
                'Title',
                'Date',
                'Volume',
                'Issue',
                'Edition',
                'Handle',
                'Presentation Set',
                'Copyright Notice',
                'Terms of Use',
                'Rights Statement',
                'Rights Holder',
                'FILES',
                'ITEM_FILES',
            ],
        ),
    ],
)
def test_make_template(runner, config_file_name, plastron_context, model_name, expected_header_fields):
    template_file = tempfile.NamedTemporaryFile(delete=False)

    result = runner.invoke(main, ['-c', config_file_name, 'import', '--make-template', template_file.name, '--model', model_name])
    assert result.exit_code == 0

    with open(template_file.name, 'r') as template_file:
        template_file.seek(0)

        csv_reader = DictReader(template_file)
        header_fields = csv_reader.fieldnames
        os.unlink(template_file.name)

        assert header_fields == expected_header_fields
