from rdflib import Graph, URIRef

from plastron.models.fedora import FixityCheck


def test_fixity_success(datadir):
    graph = Graph()
    graph.parse(datadir / 'fixity_success.ttl', format='ttl')
    check = FixityCheck(
        uri='https://fcrepo.lib.umd.edu/fcrepo/rest/pcdm/f6/26/53/6e/f626536e-4aa4-4f01-9bf6-83be5fccc2c1',
        graph=graph,
    )
    details = check.fixity_details.object
    assert details.is_success
    assert details.timestamp.isoformat() == '2026-08-05T19:55:20.947000+00:00'
    assert str(details.outcome) == 'SUCCESS'
    assert details.digest.value == URIRef('urn:sha1:40ae63dfbb6460ec44c3ecb60b0eac8970f0237a')
    assert int(details.size.value) == 739562
    assert str(details.digest_algorithm) == 'SHA-1'


def test_fixity_failure(datadir):
    graph = Graph()
    graph.parse(datadir / 'fixity_failure.ttl', format='ttl')
    check = FixityCheck(
        uri='https://fcrepo.lib.umd.edu/fcrepo/rest/dc/2023/1/5a/60/72/70/5a607270-e618-456a-b270-698be3fe706b/m/G88_DCS5/f/3gg06-rU',
        graph=graph,
    )
    details = check.fixity_details.object
    assert details.is_success is False
    assert details.timestamp.isoformat() == '2026-08-05T20:06:22.106000+00:00'
    assert {str(v) for v in details.outcome.values} == {'BAD_CHECKSUM', 'BAD_SIZE'}
    assert details.digest.value == URIRef('urn:sha1:da39a3ee5e6b4b0d3255bfef95601890afd80709')
    assert int(details.size.value) == 0
    assert str(details.digest_algorithm) == 'SHA-1'
