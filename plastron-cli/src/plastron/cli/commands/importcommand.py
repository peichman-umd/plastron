import csv
import logging
from collections.abc import Generator
from typing import TextIO, Any

import click

from plastron.jobs import Jobs
from plastron.jobs.importjob import ImportConfig, ImportJob
from plastron.jobs.importjob.ndnp import NDNPBatch, write_import_csv
from plastron.models import ModelClassNotFoundError, get_model_from_name
from plastron.utils import datetimestamp, uri_or_curie

logger = logging.getLogger(__name__)


def write_model_template(model_name: str, template_file: TextIO):
    try:
        model_class = get_model_from_name(model_name)
    except ModelClassNotFoundError as e:
        raise RuntimeError(f'Cannot find model class named {model_name}') from e
    if not hasattr(model_class, 'HEADER_MAP'):
        raise RuntimeError(f'{model_class.__name__} has no HEADER_MAP, cannot create template')

    logger.info(f'Writing template for the {model_class.__name__} model to {template_file.name}')
    writer = csv.writer(template_file)
    writer.writerow(parse_model_header_map(model_class) + ['FILES', 'ITEM_FILES'])


def parse_model_header_map(model_class):
    """
    Returns a list of fields to use as column headers for the CSV template file
    derived from the HEADER_MAP of the given model class.
    """
    header_fields = []

    for header in model_class.HEADER_MAP.values():
        if isinstance(header, dict):
            # Every value in a header map dictionary is assumed to be a field
            # name that should be used by the CSV file.
            for value in header.values():
                header_fields.append(value)
        else:
            header_fields.append(header)

    return header_fields


@click.command(help='Import new or updated objects into the repository')
@click.option('-m', '--model', help='data model to use')
@click.option('-l', '--limit', help='limit the number of rows to read from the import file', type=int)
@click.option(
    '-%',
    '--percent',
    'percentage',
    help=(
        'select an evenly spaced subset of items to import; '
        'the size of this set will be as close as possible '
        'to the specified percentage of the total items'
    ),
    type=click.IntRange(min=1, max=99),
)
@click.option('--validate-only', help='only validate, do not do the actual import', is_flag=True)
@click.option(
    '--make-template',
    'template_file',
    help='create a CSV template for the given model',
    metavar='FILENAME',
    type=click.File(mode='w', lazy=True),
)
@click.option(
    '--convert-from',
    help='use a pre-processor to transform another data format into an import job',
    type=click.Choice(['ndnp']),
)
@click.option(
    '--convert-option',
    '-o',
    'convert_params',
    help='set a parameter to used by the --convert-from pre-processor; repeatable',
    type=(str, str),
    metavar='NAME VALUE',
    multiple=True,
)
@click.option(
    '--access',
    help='URI or CURIE of the access class to apply to new items',
    type=uri_or_curie,
    metavar='URI|CURIE',
)
@click.option('--member-of', help='URI of the object that new items are PCDM members of', metavar='URI')
@click.option(
    '--binaries-location',
    help=(
        'where to find binaries; either a path to a directory, '
        'a "zip:<path to zipfile>" URI, an SFTP URI in the form '
        '"sftp://<user>@<host>/<path to dir>", or a URI in the '
        'form "zip+sftp://<user>@<host>/<path to zipfile>"'
    ),
    metavar='LOCATION',
)
@click.option(
    '--container',
    help='parent container for new items; defaults to the RELPATH in the repo configuration file',
    metavar='PATH',
)
@click.option('--job-id', help='unique identifier for this job; defaults to "import-{timestamp}"')
@click.option('--resume', help='resume a job that has been started; requires --job-id {id} to be present', is_flag=True)
@click.option(
    '--extract-text-from',
    '-x',
    'extract_text_types',
    help='extract text from binaries of the given MIME types, and add as annotations',
    metavar='MIME_TYPES',
)
@click.option(
    '--group-by',
    'file_grouping_strategy',
    help=(
        'method for grouping related files into file groups; '
        '"rootname" (default) groups files by shared base name, '
        '"none" treats each file as a separate group'
    ),
    type=click.Choice(['rootname', 'none']),
    default='rootname',
)
@click.option(
    '--use-archival-groups',
    help='whether to create items as Fedora Archival Groups (Fedora 6+)',
    is_flag=True,
)
@click.option(
    '--publish',
    help='automatically publish all items in this import',
    is_flag=True,
)
@click.argument(
    'import_file',
    help='the file to import from',
    type=click.File(mode='r'),
    required=False,
)
@click.pass_context
def import_command(
    ctx: click.Context,
    model,
    limit,
    percentage,
    validate_only,
    template_file,
    convert_from,
    convert_params,
    access,
    member_of,
    binaries_location,
    container,
    job_id,
    resume,
    extract_text_types,
    file_grouping_strategy,
    use_archival_groups,
    publish,
    import_file,
):
    """Performs the import."""
    if template_file is not None:
        write_model_template(model, template_file)
        return

    config = ctx.obj.config.get('COMMANDS', {}).get('IMPORT', {})
    jobs = Jobs(config.get('JOBS_DIR', 'jobs'))

    if resume:
        if job_id is None:
            raise RuntimeError('Resuming a job requires a job id')

        logger.info(f'Resuming saved job {job_id}')
        job = jobs.get_job(ImportJob, job_id)
    else:
        if container is None:
            raise RuntimeError('A container is required unless resuming an existing job')

        if job_id is None:
            job_id = create_job_id()

        if convert_from is not None:
            if convert_from == 'ndnp':
                params = dict(convert_params or [])
                batch = NDNPBatch(**params)
                logger.info(f'Converting NDNP batch at {batch.batch_file} to import job {job_id}')
                job = jobs.create_job(
                    job_class=ImportJob,
                    config=ImportConfig(
                        job_id=job_id,
                        model='Issue',
                        access=access,
                        member_of=member_of,
                        container=container,
                        binaries_location=str(batch.root_dir),
                        file_grouping_strategy=file_grouping_strategy,
                        use_archival_groups=use_archival_groups,
                    ),
                )
                with job.metadata_file.open(mode='w') as fh:
                    write_import_csv(batch, fh)
            else:
                raise RuntimeError(f'Unrecognized import converter "{convert_from}"')
        else:
            logger.info(f'Creating new job {job_id}')

            if import_file is None:
                raise RuntimeError('An import file is required unless resuming an existing job')

            if model is None:
                raise RuntimeError('A model is required unless resuming an existing job')

            job = jobs.create_job(
                job_class=ImportJob,
                config=ImportConfig(
                    job_id=job_id,
                    model=model,
                    access=access,
                    member_of=member_of,
                    container=container,
                    binaries_location=binaries_location,
                    file_grouping_strategy=file_grouping_strategy,
                    use_archival_groups=use_archival_groups,
                ),
            )

    logger.debug(f'Running job {job.id}')
    result = run(
        job.run(
            context=ctx.obj,
            import_file=import_file,
            limit=limit,
            percentage=percentage,
            validate_only=validate_only,
            publish=publish,
        )
    )

    for key, value in result['count'].items():
        logger.info(f'{key.title().replace("_", " ")}: {value}')


def run(proc: Generator[dict[str, Any], None, dict[str, Any]]) -> dict[str, Any]:
    result = yield from proc
    return result


def create_job_id() -> str:
    # TODO: generate a more unique id? add in user and hostname?
    return f'import-{datetimestamp()}'
