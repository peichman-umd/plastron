import collections
import csv
import logging
import os
import re
from abc import ABC
from datetime import datetime
from pathlib import Path
from typing import Union, Mapping, Sequence

DEFAULT_LOGGING_OPTIONS = {
    'version': 1,
    'formatters': {
        'full': {
            'format': '%(levelname)s|%(asctime)s|%(threadName)s|%(name)s|%(message)s'
        },
        'messageonly': {
            'format': '%(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'messageonly',
            'stream': 'ext://sys.stderr'
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'full'
        }
    },
    'loggers': {
        '__main__': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': False
        },
        'plastron': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': False
        },
        # suppress logging output from paramiko by default
        'paramiko': {
            'propagate': False
        }
    },
    'root': {
        'level': 'DEBUG'
    }
}
logger = logging.getLogger(__name__)


def datetimestamp(digits_only: bool = True) -> str:
    """Returns a string containing the current UTC timestamp. By default, it
    is only digits (`20231117151827` vs. `2023-11-17T15:18:27`). If you want
    the full ISO 8601 representation, set `digits_only` to `True`.

    ```pycon
    >>> datetimestamp()
    '20231117152014'

    >>> datetimestamp(digits_only=False)
    '2023-11-17T15:20:57'
    ```
    """
    now = str(datetime.utcnow().isoformat(timespec='seconds'))
    if digits_only:
        return re.sub(r'[^0-9]', '', now)
    else:
        return now


def envsubst(value: Union[str, list, dict], env: Mapping[str, str] = None) -> Union[str, list, dict]:
    """
    Recursively replace `${VAR_NAME}` placeholders in value with the values of the
    corresponding keys of env. If env is not given, it defaults to the environment
    variables in os.environ.

    Any placeholders that do not have a corresponding key in the env dictionary
    are left as is.

    :param value: String, list, or dictionary to search for `${VAR_NAME}` placeholders.
    :param env: Dictionary of values to use as replacements. If not given, defaults
        to `os.environ`.
    :return: If `value` is a string, returns the result of replacing `${VAR_NAME}` with the
        corresponding `value` from env. If `value` is a list, returns a new list where each
        item in `value` replaced with the result of calling `envsubst()` on that item. If
        `value` is a dictionary, returns a new dictionary where each item in `value` is replaced
        with the result of calling `envsubst()` on that item.
    """
    if env is None:
        env = os.environ
    if isinstance(value, str):
        if '${' in value:
            try:
                return value.replace('${', '{').format(**env)
            except KeyError as e:
                missing_key = str(e.args[0])
                logger.warning(f'Environment variable ${{{missing_key}}} not found')
                # for a missing key, just return the string without substitution
                return envsubst(value, {missing_key: f'${{{missing_key}}}', **env})
        else:
            return value
    elif isinstance(value, list):
        return [envsubst(v, env) for v in value]
    elif isinstance(value, dict):
        return {k: envsubst(v, env) for k, v in value.items()}
    else:
        return value


def strtobool(val: str) -> int:
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.

    This implementation is copied from distutils/util.py in Python 3.10.4,
    in order to retain this functionality once distutils is removed in
    Python 3.12. See also https://peps.python.org/pep-0632/#migration-advice
    and https://docs.python.org/3.10/whatsnew/3.10.html#distutils-deprecated.

    Note that even though this function is named `strtobool`, it actually
    returns an integer. This is copied directly from the distutils module.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))


class AppendableSequence(collections.Sequence, ABC):
    """Abstract base class for appendable sequences"""
    def append(self, _value):
        raise NotImplementedError


class NullLog(AppendableSequence):
    """Stub replacement for `ItemLog` that simply discards logged items
    and returns `False` for any containment checks."""
    def __len__(self) -> int:
        return 0

    def __getitem__(self, item):
        raise IndexError

    def __contains__(self, item):
        return False

    def append(self, _value):
        """This class just discards the given value"""
        pass


class ItemLog(AppendableSequence):
    """Log backed by a CSV file that is used to record item information,
    keyed by a particular column, with the ability to check whether a
    given key exists in the log already.

    `ItemLog` objects are iterable, and support direct indexing to a row
    by key.
    """
    def __init__(self, filename: Union[str, Path], fieldnames: Sequence[str], keyfield: str, header: bool = True):
        self.filename: Path = Path(filename)
        self.fieldnames: Sequence[str] = fieldnames
        self.keyfield: str = keyfield
        self.write_header: bool = header
        self._item_keys = set()
        self._fh = None
        self._writer = None
        if self.exists():
            self._load_keys()

    def exists(self) -> bool:
        """Returns `True` if the CSV log file exists."""
        return self.filename.is_file()

    def create(self):
        """Create the CSV log file. This will overwrite an existing file. If
        `write_header` is `True`, it will also write a header row to the file."""
        with self.filename.open(mode='w', buffering=1) as fh:
            writer = csv.DictWriter(fh, fieldnames=self.fieldnames)
            if self.write_header:
                writer.writeheader()

    def _load_keys(self):
        for row in iter(self):
            self._item_keys.add(row[self.keyfield])

    def __iter__(self):
        try:
            with self.filename.open(mode='r', buffering=1) as fh:
                reader = csv.DictReader(fh)
                # check the validity of the map file data
                if not reader.fieldnames == self.fieldnames:
                    logger.warning(
                        f'Fieldnames in {self.filename} do not match expected fieldnames; '
                        f'expected: {self.fieldnames}; found: {reader.fieldnames}'
                    )
                # read the data from the existing file
                yield from reader
        except FileNotFoundError:
            # log file not found, so stop the iteration
            return

    @property
    def writer(self) -> csv.DictWriter:
        """CSV dictionary writer"""
        if not self.exists():
            self.create()
        if self._fh is None:
            self._fh = self.filename.open(mode='a', buffering=1)
        if self._writer is None:
            self._writer = csv.DictWriter(self._fh, fieldnames=self.fieldnames)
        return self._writer

    def append(self, row):
        """Write this `row` to the log."""
        self.writer.writerow(row)
        self._item_keys.add(row[self.keyfield])

    def writerow(self, row):
        """Alias for `append`"""
        self.append(row)

    def __contains__(self, other):
        return other in self._item_keys

    def __len__(self):
        return len(self._item_keys)

    def __getitem__(self, item):
        for n, row in enumerate(self):
            if n == item:
                return row
        raise IndexError(item)


class ItemLogError(Exception):
    pass
