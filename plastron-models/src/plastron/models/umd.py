from rdflib import Namespace

from plastron.namespaces import dc, dcterms, edm, rdfs, owl, ldp, fabio, pcdm, iana, ore, ebucore, premis
from plastron.rdfmapping.decorators import rdf_type
from plastron.rdfmapping.descriptors import ObjectProperty, DataProperty
from plastron.rdfmapping.resources import RDFResource, RDFResourceBase
# from plastron.rdf import pcdm, rdf
# from plastron.rdf.authority import LabeledThing
# from plastron.rdf.pcdm import Page
from plastron.validation import is_edtf_formatted, is_valid_iso639_code, is_handle

umdtype = Namespace('http://vocab.lib.umd.edu/datatype#')
umdform = Namespace('http://vocab.lib.umd.edu/form#')


class LabeledThing(RDFResource):
    label = DataProperty(rdfs.label, required=True)
    same_as = ObjectProperty(owl.sameAs)


def is_from_vocabulary(vocab_uri):
    #subjects = get_subjects(vocab_uri)

    def _value_from_vocab(value):
        return True  # value in subjects

    _value_from_vocab.__doc__ = f'from vocabulary {vocab_uri}'
    return _value_from_vocab


class LDPContainer(RDFResource):
    contains = ObjectProperty(ldp.contains, repeatable=True)


class AggregationMixin(RDFResourceBase):
    first = ObjectProperty(iana.first, required=True, cls='Proxy')
    last = ObjectProperty(iana.last, required=True, cls='Proxy')


@rdf_type(pcdm.Object)
class PCDMObject(RDFResource, AggregationMixin):
    title = DataProperty(dcterms.title)
    has_member = ObjectProperty(pcdm.hasMember, repeatable=True, cls='PCDMObject')
    member_of = ObjectProperty(pcdm.memberOf, repeatable=True, cls='PCDMObject')
    has_file = ObjectProperty(pcdm.hasFile, repeatable=True, cls='PCDMFile')


@rdf_type(pcdm.File)
class PCDMFile(RDFResource):
    title = DataProperty(dcterms.title)
    file_of = ObjectProperty(pcdm.fileOf, repeatable=True, cls=PCDMObject)
    mime_type = DataProperty(ebucore.hasMimeType)
    filename = DataProperty(ebucore.filename)
    size = DataProperty(premis.hasSize)

    def __str__(self):
        return str(self.title or self.uri)


class Item(PCDMObject):
    object_type = ObjectProperty(
        dcterms.type,
        required=True,
        validate=is_from_vocabulary('http://purl.org/dc/dcmitype/'),
    )
    identifier = DataProperty(dcterms.identifier, required=True, repeatable=True)
    rights = ObjectProperty(
        dcterms.rights,
        required=True,
        validate=is_from_vocabulary('http://vocab.lib.umd.edu/rightsStatement#'),
    )
    title = DataProperty(dcterms.title, required=True)
    format = ObjectProperty(edm.hasType, validate=is_from_vocabulary('http://vocab.lib.umd.edu/form#'))
    archival_collection = ObjectProperty(
        dcterms.isPartOf,
        validate=is_from_vocabulary('http://vocab.lib.umd.edu/collection#'),
    )
    date = DataProperty(dc.date, validate=is_edtf_formatted)
    description = DataProperty(dcterms.description)
    alternate_title = DataProperty(dcterms.alternative, repeatable=True)
    creator = ObjectProperty(dcterms.creator, repeatable=True, embed=True, cls=LabeledThing)
    contributor = ObjectProperty(dcterms.contributor, repeatable=True, embed=True, cls=LabeledThing)
    publisher = ObjectProperty(dcterms.publisher, repeatable=True, embed=True, cls=LabeledThing)
    location = ObjectProperty(dcterms.spatial, repeatable=True, embed=True, cls=LabeledThing)
    extent = DataProperty(dcterms.extent, repeatable=True)
    subject = ObjectProperty(dcterms.subject, repeatable=True, embed=True, cls=LabeledThing)
    language = DataProperty(dc.language, repeatable=True, validate=is_valid_iso639_code)
    rights_holder = ObjectProperty(dcterms.rightsHolder, repeatable=True, embed=True, cls=LabeledThing)
    bibliographic_citation = DataProperty(dcterms.bibliographicCitation)
    accession_number = DataProperty(dcterms.identifier, datatype=umdtype.accessionNumber)
    handle = DataProperty(dcterms.identifier, datatype=umdtype.handle, validate=is_handle)

    HEADER_MAP = {
        'object_type': 'Object Type',
        'identifier': 'Identifier',
        'rights': 'Rights Statement',
        'title': 'Title',
        'format': 'Format',
        'archival_collection': 'Archival Collection',
        'date': 'Date',
        'description': 'Description',
        'alternate_title': 'Alternate Title',
        'creator.label': 'Creator',
        'creator.same_as': 'Creator URI',
        'contributor.label': 'Contributor',
        'contributor.same_as': 'Contributor URI',
        'publisher.label': 'Publisher',
        'publisher.same_as': 'Publisher URI',
        'location.label': 'Location',
        'extent': 'Extent',
        'subject.label': 'Subject',
        'language': 'Language',
        'rights_holder.label': 'Rights Holder',
        'bibliographic_citation': 'Collection Information',
        'accession_number': 'Accession Number',
        'handle': 'Handle',
    }

    def __str__(self):
        return str(self.title)


@rdf_type(fabio.Page)
class Page(PCDMObject):
    title = DataProperty(dcterms.title)
    number = DataProperty(fabio.hasSequenceIdentifier)

    def __str__(self):
        return str(self.title or self.uri)


@rdf_type(ore.Proxy)
class Proxy(RDFResource):
    title = DataProperty(dcterms.title)
    prev = ObjectProperty(iana.prev, cls='Proxy')
    next = ObjectProperty(iana.next, cls='Proxy')
    proxy_for = ObjectProperty(ore.proxyFor, cls=RDFResourceBase)
    proxy_in = ObjectProperty(ore.proxyIn, cls=RDFResourceBase)
