import json
import logging
from typing import Generator, Any, Dict

from plastron.jobs.updatejob import UpdateJob
from plastron.models import get_model_class
from plastron.rdf import parse_predicate_list
from plastron.repo import Repository
from plastron.stomp.messages import PlastronCommandMessage
from plastron.utils import strtobool

logger = logging.getLogger(__name__)


def parse_message(message: PlastronCommandMessage) -> Dict[str, Any]:
    message.body = message.body.encode('utf-8').decode('utf-8-sig')
    body = json.loads(message.body)
    uris = body['uris']
    sparql_update = body['sparql_update']
    validate = bool(strtobool(message.args.get('validate', 'false')))
    model = message.args.get('model', None)
    recursive = message.args.get('recursive', None)

    if validate and not model:
        raise RuntimeError("Model must be provided when performing validation")

    # Retrieve the model to use for validation
    model_class = get_model_class(model) if model else None

    traverse = parse_predicate_list(recursive) if recursive is not None else []
    return {
        'uris': uris,
        'sparql_update': sparql_update,
        'model_class': model_class,
        'traverse': traverse,
        'dry_run': bool(strtobool(message.args.get('dry-run', 'false'))),
        # Default to no transactions, due to LIBFCREPO-842
        'use_transactions': not bool(strtobool(message.args.get('no-transactions', 'true'))),
    }


def update(
        repo: Repository,
        _config: Dict[str, Any],
        message: PlastronCommandMessage,
) -> Generator[Dict[str, str], None, Dict[str, Any]]:
    return UpdateJob(repo=repo, **parse_message(message)).run()
