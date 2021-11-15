import logging
import urllib.parse
from pathlib import Path

from flask import Flask, request, url_for
from pyparsing import ParseException
from werkzeug.exceptions import BadRequest, NotAcceptable, NotFound, UnsupportedMediaType

import plastron.models
from plastron.commands.importcommand import validate
from plastron.http import Repository
from plastron.jobs import ConfigMissingError, ImportJob, JobError, ModelClassNotFoundError

logger = logging.getLogger(__name__)


def problem_detail(status=400, **kwargs):
    """
    RFC 7807 style problem detail JSON response
    """
    return dict(status=status, **kwargs), status


def job_url(job_id):
    return url_for('show_job', _external=True, job_id=job_id)


def items(log):
    return {
        'count': len(log),
        'items': [c for c in log]
    }


def latest_dropped_items(job: ImportJob):
    latest_run = job.latest_run()
    if latest_run is None:
        return {}

    return {
        'timestamp': latest_run.timestamp,
        'failed': items(latest_run.failed_items),
        'invalid': items(latest_run.invalid_items)
    }


def create_app(config):
    app = Flask(__name__)
    app.config.from_mapping(config)
    jobs_dir = Path(app.config['JOBS_DIR'])
    repo = Repository(app.config['REPOSITORY'])

    def get_job(job_id: str):
        job = ImportJob(urllib.parse.unquote(job_id), str(jobs_dir))
        if not job.dir_exists:
            raise NotFound
        return job

    @app.route('/jobs')
    def list_jobs():
        if not jobs_dir.exists():
            logger.warning(f'Jobs directory "{jobs_dir.absolute()}" does not exist; returning empty list')
            return {'jobs': []}
        job_ids = sorted(f.name for f in jobs_dir.iterdir() if f.is_dir())
        return {'jobs': [{'@id': job_url(job_id), 'job_id': job_id} for job_id in job_ids]}

    @app.route('/jobs/<path:job_id>')
    def show_job(job_id):
        job = get_job(job_id)
        try:
            job.load_config()
        except ConfigMissingError as e:
            logger.warning(f'Cannot open config file {job.config_filename} for job {job}')
            # TODO: more complete information in the response body?
            raise NotFound

        try:
            return {
                '@id': job_url(job_id),
                **job.config,
                'runs': job.runs,
                'completed': items(job.completed_log),
                'dropped': latest_dropped_items(job),
                'total': job.metadata().total
            }
        except JobError as e:
            raise NotFound from e

    @app.route('/resources/<path:resource_path>', methods=['PATCH'])
    def update_resource(resource_path):
        if request.content_type != 'application/sparql-update':
            raise UnsupportedMediaType

        sparql_update = request.data
        uri = repo.endpoint + '/' + resource_path
        graph = repo.get_graph(uri)

        model = request.args.get('model', None)
        if model is not None:
            # validate according to the given content model
            try:
                model_class = getattr(plastron.models, model)
            except AttributeError:
                return problem_detail(
                    status=404,
                    title='Unrecognized content-model',
                    detail=f'{model} is not a recognized content-model name'
                )
            try:
                # Apply the update in-memory to the resource graph
                graph.update(sparql_update.decode())
            except ParseException as e:
                raise BadRequest from e

            # Validate the updated in-memory Graph using the model
            item = model_class.from_graph(graph, subject=uri)
            validation_result = validate(item)
            if not validation_result.is_valid():
                errors = list(validation_result.failed())
                # return RFC 7807 style problem detail JSON response
                return problem_detail(
                    title='Content-model validation failed',
                    detail=f'{len(errors)} validation error(s) prevented update of {uri} with content-model {model}',
                    validation_errors=errors,
                    model=model,
                    resource=uri
                )

        headers = {'Content-Type': 'application/sparql-update'}
        response = repo.patch(uri, data=sparql_update, headers=headers)
        if response.ok:
            return '', 204
        return problem_detail(
            status=500,
            title='Repository error',
            detail=str(response)
        )

    return app
