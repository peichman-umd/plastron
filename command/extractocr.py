from classes.exceptions import RESTAPIException
from classes import util
from handler import ndnp
import logging

logger = logging.getLogger(__name__)
now = datetime.utcnow().strftime('%Y%m%d%H%M%S')

def run(fcrepo, args):
    fieldnames = ['uri', 'timestamp']

    # read the log of completed items
    try:
        completed = util.ItemLog('logs/annotated.csv', fieldnames, 'uri')
    except Exception as e:
        logger.error('Non-standard map file specified: {0}'.format(e))
        sys.exit(1)

    logger.info('Found {0} completed items'.format(len(completed)))

    if args.ignore is not None:
        try:
            ignored = util.ItemLog(args.ignore, fieldnames, 'uri')
        except Exception as e:
            logger.error('Non-standard ignore file specified: {0}'.format(e))
            sys.exit(1)
    else:
        ignored = []

    skipfile = 'logs/skipped.extractocr.{0}.csv'.format(now)
    skipped = util.ItemLog(skipfile, fieldnames, 'uri')

    with fcrepo.at_path('/annotations'):
        for line in sys.stdin:
            uri = line.rstrip('\n')
            if uri in completed:
                continue
            elif uri in ignored:
                logger.debug('Ignoring {0}'.format(uri))
                continue

            is_extracted = False
            try:
                is_extracted = extract(fcrepo, uri)
            except RESTAPIException as e:
                logger.error(
                    "Unable to commit or rollback transaction, aborting"
                    )
                sys.exit(1)

            row = {
                'uri': uri,
                'timestamp': str(datetime.utcnow())
                }

            if is_extracted:
                completed.writerow(row)
            else:
                skipped.writerow(row)

def extract(fcrepo, uri):
    fcrepo.open_transaction()
    try:
        logger.info("Getting {0} from repository".format(uri))
        page = ndnp.Page.from_repository(fcrepo, uri)
        logger.info("Creating annotations for page {0}".format(page.title))
        for annotation in page.textblocks():
            annotation.create_object(fcrepo)
            annotation.update_object(fcrepo)

        fcrepo.commit_transaction()
        return True

    except (RESTAPIException, DataReadException) as e:
        # if anything fails during item creation or commiting the transaction
        # attempt to rollback the current transaction
        # failures here will be caught by the main loop's exception handler
        # and should trigger a system exit
        logger.error("OCR extraction failed: {0}".format(e))
        fcrepo.rollback_transaction()
        logger.warn('Transaction rolled back. Continuing load.')
