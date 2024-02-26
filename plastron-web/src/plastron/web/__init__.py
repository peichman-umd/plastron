import logging
import os
import yaml
import urllib.parse
from pathlib import Path
from argparse import Namespace
from flask import Flask, url_for
from werkzeug.exceptions import NotFound

from plastron.cli.context import PlastronContext
from plastron.jobs.importjob import ImportJob, ImportJobs
from plastron.jobs import JobError, JobConfigError, JobNotFoundError
from plastron.web.activitystream import activitystream_bp
from plastron.utils import envsubst

logger = logging.getLogger(__name__)


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


def create_app(config_file: str):
    app = Flask(__name__)
    with open(config_file, "r") as stream:
        config = envsubst(yaml.safe_load(stream))
        app.config['CONTEXT'] = Namespace(obj=PlastronContext(config=config, args=Namespace(delegated_user=None)))
    jobs_dir = Path(os.environ.get('JOBS_DIR', 'jobs'))
    jobs = ImportJobs(directory=jobs_dir)
    app.register_blueprint(activitystream_bp)

    def get_job(job_id: str):
        return jobs.get_job(urllib.parse.unquote(job_id))

    @app.route('/jobs')
    def list_jobs():
        if not jobs_dir.exists():
            logger.warning(f'Jobs directory "{jobs_dir.absolute()}" does not exist; returning empty list')
            return {'jobs': []}
        job_ids = sorted(f.name for f in jobs_dir.iterdir() if f.is_dir())
        return {'jobs': [{'@id': job_url(job_id), 'job_id': job_id} for job_id in job_ids]}

    @app.route('/jobs/<path:job_id>')
    def show_job(job_id):
        try:
            job = get_job(job_id)
            job.load_config()
        except JobNotFoundError:
            logger.warning(f'Job {job_id} not found')
            raise NotFound
        except JobConfigError:
            logger.warning(f'Cannot open config file for job {job_id}')
            # TODO: more complete information in the response body?
            raise NotFound

        try:
            return {
                '@id': job_url(job_id),
                **vars(job.config),
                'runs': job.runs,
                'completed': items(job.completed_log),
                'dropped': latest_dropped_items(job),
                'total': job.get_metadata().total
            }
        except JobError as e:
            raise NotFound from e

    return app
