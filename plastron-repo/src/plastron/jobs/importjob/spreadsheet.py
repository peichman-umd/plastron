import csv
import logging
import re
from collections import defaultdict, OrderedDict
from collections.abc import Sized, Container
from dataclasses import dataclass
from os.path import splitext, basename
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union, Mapping, Type, Iterator, NamedTuple, Protocol
from uuid import uuid4

from rdflib import URIRef, Literal
from rdflib.util import from_n3

from plastron.files import FileSpec, FileGroup
from plastron.jobs import JobError
from plastron.namespaces import get_manager
from plastron.rdfmapping.descriptors import Property, DataProperty
from plastron.rdfmapping.embed import EmbeddedObject
from plastron.rdfmapping.resources import RDFResourceBase, RDFResourceType
from plastron.repo import DataReadError, Repository, RepositoryResource
from plastron.serializers import CSVSerializer
from plastron.serializers.csv import flatten_headers, unflatten, not_empty, split_escaped, build_lookup_index

nsm = get_manager()
logger = logging.getLogger(__name__)


@dataclass
class ColumnSpec:
    attrs: str
    header: str
    prop: Property
    lang_code: Optional[str] = None
    datatype: Optional[URIRef] = None


class MetadataError(JobError):
    pass


class LineReference(NamedTuple):
    """Filename-line number pairing. Stringifies to `{filename}:{line number}`
    (e.g., `job-0123/import.csv:29`)"""
    filename: str
    line_number: int

    def __str__(self):
        return f'{self.filename}:{self.line_number}'


def build_fields(fieldnames, model_class) -> Dict[str, List[ColumnSpec]]:
    property_attrs = flatten_headers(model_class.HEADER_MAP)
    fields = defaultdict(list)
    # group typed and language-tagged columns by their property attribute
    for header in fieldnames:
        # make sure we skip the system columns
        if header in CSVSerializer.SYSTEM_HEADERS:
            continue

        if '[' in header:
            # this field has a language tag
            # header format is "Header Label [Language Label]"
            header_label, language_label = re.search(r'^([^[]+)\s+\[(.+)]$', header).groups()
            try:
                attrs = property_attrs[header_label]
            except KeyError as e:
                raise DataReadError(f'Unknown header "{header}" in import file.') from e
            # if the language label isn't a name in the LANGUAGE_CODES table,
            # assume that it is itself a language code
            lang_code = CSVSerializer.LANGUAGE_CODES.get(language_label, language_label)
            fields[attrs].append(ColumnSpec(
                attrs=attrs,
                header=header,
                prop=get_final_prop(model_class, attrs.split('.')),
                lang_code=lang_code,
                datatype=None,
            ))
        elif '{' in header:
            # this field has a datatype
            # header format is "Header Label {Datatype Label}
            header_label, datatype_label = re.search(r'^([^{]+)\s+{(.+)}$', header).groups()
            try:
                attrs = property_attrs[header_label]
            except KeyError as e:
                raise DataReadError(f'Unknown header "{header}" in import file.') from e
            # the datatype label should either be a key in the lookup table,
            # or an n3-abbreviated URI of a datatype
            try:
                datatype_uri = CSVSerializer.DATATYPE_URIS.get(datatype_label, from_n3(datatype_label, nsm=nsm))
                if not isinstance(datatype_uri, URIRef):
                    raise DataReadError(f'Unknown datatype "{datatype_label}" in "{header}" in import file.')
            except KeyError as e:
                raise DataReadError(f'Unknown datatype "{datatype_label}" in "{header}" in import file.') from e

            fields[attrs].append(ColumnSpec(
                attrs=attrs,
                header=header,
                prop=get_final_prop(model_class, attrs.split('.')),
                lang_code=None,
                datatype=datatype_uri,
            ))
        else:
            # no language tag or datatype
            if header not in property_attrs:
                raise DataReadError(f'Unrecognized header "{header}" in import file.')
            # check for a default datatype defined in the model
            attrs = property_attrs[header]
            prop = get_final_prop(model_class, attrs.split('.'))
            if prop is not None and isinstance(prop, DataProperty):
                datatype_uri = prop.datatype
            else:
                datatype_uri = None
            fields[attrs].append(ColumnSpec(
                attrs=attrs,
                header=header,
                prop=prop,
                lang_code=None,
                datatype=datatype_uri,
            ))
    return fields


def get_final_prop(model_class: Type[RDFResourceType], attrs: List[str]) -> str:
    next_attr_name = attrs.pop(0)
    next_attr = getattr(model_class, next_attr_name)
    if not attrs:
        return next_attr
    return get_final_prop(next_attr.object_class, attrs)


def build_file_groups(filenames_string: str) -> Dict[str, FileGroup]:
    file_groups = OrderedDict()
    if filenames_string.strip() == '':
        return file_groups
    for filename in filenames_string.split(';'):
        root, ext = splitext(basename(filename))
        if root not in file_groups:
            file_groups[root] = FileGroup(rootname=root)
        file_groups[root].files.append(FileSpec(name=filename))
    logger.debug(f'Found {len(file_groups.keys())} unique file basename(s)')
    return file_groups


def parse_value_string(value_string, column: ColumnSpec) -> List[Union[Literal, URIRef]]:
    values = []
    # filter out empty strings, so we don't get spurious empty values in the properties
    for value in filter(not_empty, split_escaped(value_string, separator='|')):
        if isinstance(column.prop, DataProperty):
            # default to the property's defined datatype
            # if it was not specified in the column header
            values.append(Literal(value, lang=column.lang_code, datatype=(column.datatype or column.prop.datatype)))
        else:
            values.append(URIRef(value))
    return values


@dataclass
class InvalidRow:
    line_reference: LineReference
    reason: str


def create_embedded_object(attr: str, item: RDFResourceBase) -> Tuple[str, RDFResourceBase]:
    # create new embedded objects (a.k.a hash resources) that are not in the index
    fragment_id = str(uuid4())
    obj = EmbeddedObject(getattr(item, attr).object_class, fragment_id=fragment_id).embed(item)
    return fragment_id, obj


class Bucket(Sized, Container, Protocol):
    pass


class Row:
    def __init__(
            self,
            spreadsheet: 'MetadataSpreadsheet',
            line_reference: LineReference,
            row_number: int,
            data: Mapping[str, str],
            identifier_column: str,
    ):
        self.spreadsheet = spreadsheet
        self.line_reference = line_reference
        self.number = row_number
        self.data = data
        self.identifier_column = identifier_column
        self._file_groups = build_file_groups(self.data.get('FILES', ''))

    def __getitem__(self, item):
        return self.data[item]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def parse_value(self, column: ColumnSpec) -> List[Union[Literal, URIRef]]:
        return parse_value_string(self[column.header], column)

    def get_object(self, repo: Repository, read_from_repo: bool = False) -> RDFResourceType:
        """Gets an RDF resource to be imported, based on the metadata in this row.

        :param repo: the repository configuration
        :param read_from_repo: If true, will fetch existing object from the
                    repository.
        """
        if self.uri is not None:
            # resource with the URI from the spreadsheet
            resource = repo[self.uri]
            if read_from_repo:
                # unless we are only validating,
                # read the object from the repo
                resource.read()
        else:
            # no URI in the CSV means we will create a new object
            logger.info(f'No URI found for {self.line_reference}; will create new resource')
            # create a new object (will create in the repo later)
            resource = RepositoryResource(repo=repo)

        # build the lookup index to map hash URI objects
        # to their correct positional locations
        row_index = build_lookup_index(self.index_string)
        params = unflatten(self.data, self.spreadsheet.model_class, self.spreadsheet.model_class.HEADER_MAP, row_index)
        item: RDFResourceType = self.spreadsheet.model_class(uri=self.uri, graph=resource.graph)
        item.set_properties(**params)

        return item

    @property
    def identifier(self):
        return self.data[self.identifier_column]

    @property
    def has_uri(self):
        return 'URI' in self.data and self.data['URI'].strip() != ''

    @property
    def uri(self) -> URIRef:
        return URIRef(self.data['URI']) if self.has_uri else None

    @property
    def has_files(self):
        return 'FILES' in self.data and self.data['FILES'].strip() != ''

    @property
    def has_item_files(self):
        return 'ITEM_FILES' in self.data and self.data['ITEM_FILES'].strip() != ''

    @property
    def filenames(self):
        return self.data['FILES'].strip().split(';') if self.has_files else []

    @property
    def file_groups(self):
        return self._file_groups

    @property
    def item_filenames(self):
        return self.data['ITEM_FILES'].strip().split(';') if self.has_item_files else []

    @property
    def index_string(self):
        return self.data.get('INDEX')


class MetadataSpreadsheet:
    """
    Iterable sequence of rows from the metadata CSV file of an import job.
    """

    def __init__(self, metadata_filename: Union[Path, str], model_class: Type[RDFResourceType]):
        self.metadata_filename = metadata_filename
        self.metadata_file = None
        self.model_class = model_class

        try:
            self.metadata_file = open(metadata_filename, 'r')
        except FileNotFoundError as e:
            raise MetadataError(f'Cannot read metadata file "{metadata_filename}": {e}') from e

        self.csv_file = csv.DictReader(self.metadata_file)

        try:
            self.fields = build_fields(self.fieldnames, self.model_class)
        except DataReadError as e:
            raise RuntimeError(str(e)) from e

        self.validation_reports: List[Mapping] = []
        self.skipped = 0
        self.subset_to_load = None

        self.total = None
        self.row_count = 0
        self.errors = 0

        if self.metadata_file.seekable():
            # get the row count of the file, then rewind the CSV file
            self.total = sum(1 for _ in self.csv_file)
            self._rewind_csv_file()
        else:
            # file is not seekable, so we can't get a row count in advance
            self.total = None

    def _rewind_csv_file(self):
        # rewind the file and re-create the CSV reader
        self.metadata_file.seek(0)
        self.csv_file = csv.DictReader(self.metadata_file)

    @property
    def has_binaries(self) -> bool:
        return 'FILES' in self.fieldnames

    @property
    def fieldnames(self):
        return self.csv_file.fieldnames

    @property
    def identifier_column(self):
        return self.model_class.HEADER_MAP['identifier']

    def should_load(self, line) -> bool:
        """Whether the given line is part of the subset of lines to load."""
        return self.subset_to_load is None or line[self.identifier_column] in self.subset_to_load

    def rows(
            self,
            limit: int = None,
            percentage: int = None,
            completed: Bucket = None,
    ) -> Iterator[Union[Row, InvalidRow]]:
        """Iterator over the rows in this spreadsheet.

        :param limit: maximum row number to return
        :param percentage: percentage of rows to load, as an integer 1-100
        :param completed: record of already completed items; typically an ItemLog instance, but it
          only has to support `__len__()` and `__contains__(identifier)`
        """

        if completed is None:
            completed = []

        if percentage is not None:
            if not self.metadata_file.seekable():
                raise RuntimeError('Cannot execute a percentage load using a non-seekable file')
            identifier_column = self.model_class.HEADER_MAP['identifier']
            identifiers = [
                row[identifier_column] for row in self.csv_file if row[identifier_column] not in completed
            ]
            self._rewind_csv_file()

            if len(identifiers) == 0:
                logger.info('No items remaining to load')
                self.subset_to_load = []
            else:
                target_count = int(((percentage / 100) * self.total))
                logger.info(f'Attempting to load {target_count} items ({percentage}% of {self.total})')
                if len(identifiers) > target_count:
                    # evenly space the items to load among the remaining items
                    step_size = int((100 * (1 - (len(completed) / self.total))) / percentage)
                else:
                    # load all remaining items
                    step_size = 1
                self.subset_to_load = identifiers[::step_size]

        for row_number, line in enumerate(self.csv_file, 1):
            if limit is not None and row_number > limit:
                logger.info(f'Stopping after {limit} rows')
                break

            if not self.should_load(line):
                continue

            line_reference = LineReference(filename=str(self.metadata_filename), line_number=row_number + 1)
            logger.debug(f'Processing {line_reference}')
            self.row_count += 1

            if any(v is None for v in line.values()):
                self.errors += 1
                self.validation_reports.append({
                    'line': line_reference,
                    'is_valid': False,
                    'error': f'Line {line_reference} has the wrong number of columns'
                })
                yield InvalidRow(line_reference=line_reference, reason='Wrong number of columns')
                continue

            row = Row(self, line_reference, row_number, line, self.identifier_column)

            if row.identifier in completed:
                logger.info(f'Already loaded "{row.identifier}" from {line_reference}, skipping')
                self.skipped += 1
                continue

            yield row

        if self.total is None:
            # if we weren't able to get the total count before,
            # use the final row count as the total count for the
            # job completion message
            self.total = self.row_count
