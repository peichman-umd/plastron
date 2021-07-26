from rdflib import Namespace, Graph
from rdflib.namespace import NamespaceManager

# useful namespaces for use with rdflib code
acl       = Namespace('http://www.w3.org/ns/auth/acl#')
bibo      = Namespace('http://purl.org/ontology/bibo/')
carriers  = Namespace('http://id.loc.gov/vocabulary/carriers/')
dc        = Namespace('http://purl.org/dc/elements/1.1/')
dcmitype  = Namespace('http://purl.org/dc/dcmitype/')
dcterms   = Namespace('http://purl.org/dc/terms/')
ebucore   = Namespace('http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#')
edm       = Namespace('http://www.europeana.eu/schemas/edm/')
ex        = Namespace('http://www.example.org/terms/')
fabio     = Namespace('http://purl.org/spar/fabio/')
fedora    = Namespace('http://fedora.info/definitions/v4/repository#')
foaf      = Namespace('http://xmlns.com/foaf/0.1/')
geo       = Namespace('http://www.w3.org/2003/01/geo/wgs84_pos#')
iana      = Namespace('http://www.iana.org/assignments/relation/')
ldp       = Namespace('http://www.w3.org/ns/ldp#')
ndnp      = Namespace('http://chroniclingamerica.loc.gov/terms/')
oa        = Namespace('http://www.w3.org/ns/oa#')
ore       = Namespace('http://www.openarchives.org/ore/terms/')
owl       = Namespace('http://www.w3.org/2002/07/owl#')
pcdm      = Namespace('http://pcdm.org/models#')
pcdmuse   = Namespace('http://pcdm.org/use#')
premis    = Namespace('http://www.loc.gov/premis/rdf/v1#')
prov      = Namespace('http://www.w3.org/ns/prov#')
rdf       = Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
rdfs      = Namespace('http://www.w3.org/2000/01/rdf-schema#')
rel       = Namespace('http://id.loc.gov/vocabulary/relators/')
sc        = Namespace('http://www.shared-canvas.org/ns/')
skos      = Namespace('http://www.w3.org/2004/02/skos/core#')
umdaccess = Namespace('http://vocab.lib.umd.edu/access#')
webac     = Namespace('http://fedora.info/definitions/v4/webac#')
xsd       = Namespace('http://www.w3.org/2001/XMLSchema#')


def get_manager(graph=None):
    if graph is None:
        graph = Graph()
    m = NamespaceManager(graph)
    m.bind('acl', acl)
    m.bind('bibo', bibo)
    m.bind('carriers', carriers)
    m.bind('dc', dc)
    m.bind('dcmitype', dcmitype)
    m.bind('dcterms', dcterms)
    m.bind('ebucore', ebucore)
    m.bind('edm', edm)
    m.bind('ex', ex)
    m.bind('fabio', fabio)
    m.bind('fedora', fedora)
    m.bind('foaf', foaf)
    m.bind('geo', geo)
    m.bind('iana', iana)
    m.bind('ldp', ldp)
    m.bind('ndnp', ndnp)
    m.bind('oa', oa)
    m.bind('ore', ore)
    m.bind('owl', owl)
    m.bind('pcdm', pcdm)
    m.bind('pcdmuse', pcdmuse)
    m.bind('premis', premis)
    m.bind('prov', prov)
    m.bind('rdf', rdf)
    m.bind('rdfs', rdfs)
    m.bind('rel', rel)
    m.bind('sc', sc)
    m.bind('skos', skos)
    m.bind('umdaccess', umdaccess)
    m.bind('webac', webac)
    m.bind('xsd', xsd)
    return m
