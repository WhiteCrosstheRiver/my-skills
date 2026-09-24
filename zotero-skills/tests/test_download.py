from pathlib import Path

import pymupdf
import pytest

from zotero_skills import download
from zotero_skills.core import read_json


def pdf_bytes():
    with pymupdf.open() as doc:
        doc.new_page().insert_text((50, 50), 'Full text fixture')
        return doc.tobytes()


class Client:
    def __init__(self):
        self.attachments = []
        self.writes = 0

    def snapshot(self, *args):
        return {'attachments': self.attachments}

    def attach(self, key, path, *args):
        self.writes += 1
        self.attachments.append({'key': 'PDF1', 'path': str(path), 'contentType': 'application/pdf'})
        return {'key': 'PDF1'}


PAPER = {'title': 'The paper', 'doi': '10.1234/test', 'item_key': 'ITEM0001', 'pdf_urls': ['https://publisher.test/a.pdf']}


def test_existing_scan_is_skipped_without_network_or_write(tmp_path):
    file = tmp_path / 'scan.pdf'; file.write_bytes(b'user file do not parse or change')
    client = Client(); client.attachments = [{'key': 'OLD', 'path': str(file), 'contentType': 'application/pdf'}]
    result = download.download_pdf(PAPER, tmp_path, client, None)
    assert result['status'] == 'skipped_existing' and client.writes == 0
    assert file.read_bytes() == b'user file do not parse or change'


def test_primary_success_never_calls_resolvers_and_repeat_skips(tmp_path, monkeypatch):
    def forbidden(*args): raise AssertionError('Unnecessary resolver')
    monkeypatch.setattr(download, 'RESOLVERS', [('forbidden', forbidden)])
    class Net:
        def get(self, *args, **kwargs): return pdf_bytes()
    client = Client()
    assert download.download_pdf(PAPER, tmp_path, client, Net())['status'] == 'downloaded'
    assert download.download_pdf(PAPER, tmp_path, client, None)['status'] == 'skipped_existing'
    assert client.writes == 1


def test_corrupt_pdf_then_html_metadata_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(download, 'RESOLVERS', [('repo', lambda *a: [{'url': 'https://repo.test/article'}])])
    class Net:
        def get(self, url, **kwargs):
            if 'publisher' in url: return b'%PDF-corrupt'
            if url.endswith('article'):
                return b'<meta name="citation_doi" content="10.1234/test"><meta name="citation_pdf_url" content="/real.pdf">'
            return pdf_bytes()
    result = download.download_pdf(PAPER, tmp_path, Client(), Net())
    assert result['status'] == 'downloaded'
    assert result['source']['url'] == 'https://repo.test/real.pdf'
    assert result['attempts'][0]['status'] == 'failed'


def test_wrong_article_html_never_followed():
    assert not download.page_links(b'<meta name="citation_doi" content="10.9999/other"><meta name="citation_pdf_url" content="/wrong.pdf">', 'https://repo.test/', PAPER)


def test_resolver_outage_is_recorded_and_next_source_works(tmp_path, monkeypatch):
    def bad(*args): raise RuntimeError('token=private')
    monkeypatch.setattr(download, 'RESOLVERS', [('outage', bad), ('repo', lambda *a: [{'url': 'https://repo.test/a.pdf'}])])
    class Net:
        def get(self, *args, **kwargs): return pdf_bytes()
    result = download.download_pdf(PAPER, tmp_path, Client(), Net(), fallback_only=True)
    assert result['status'] == 'downloaded' and 'private' not in str(result)
    assert result['attempts'][0]['provider'] == 'outage'


def test_uncertain_write_stops_and_resume_does_not_download_again(tmp_path):
    class Uncertain(Client):
        def attach(self, *args):
            super().attach(*args)
            raise TimeoutError('response lost after commit')
    class Net:
        def get(self, *args, **kwargs): return pdf_bytes()
    client = Uncertain()
    with pytest.raises(TimeoutError): download.download_pdf(PAPER, tmp_path, client, Net())
    assert read_json(tmp_path / 'pdf-download.json')['status'] == 'attaching'
    assert download.download_pdf(PAPER, tmp_path, client, None)['status'] == 'skipped_existing'
    assert client.writes == 1


def test_openalex_rejects_non_oa_and_doi_mismatch():
    class Net:
        def get(self, *a): return {'doi': 'https://doi.org/10.1234/test', 'locations': [{'pdf_url': 'https://closed.test/a.pdf', 'is_oa': False}]}
    assert download.openalex(PAPER, Net()) == []
    with pytest.raises(ValueError): download.openalex({**PAPER, 'doi': '10.1234/other'}, Net())


def test_unpaywall_without_email_does_not_fake_identity(monkeypatch):
    monkeypatch.delenv('UNPAYWALL_EMAIL', raising=False)
    monkeypatch.delenv('ZOTERO_SKILLS_CONTACT_EMAIL', raising=False)
    with pytest.raises(LookupError): download.unpaywall(PAPER, None)


def test_pmc_cloud_uses_paged_current_metadata_not_legacy_api():
    class Net:
        def get(self, url, params=None, **kwargs):
            assert 'oa.fcgi' not in url
            if 'europepmc' in url:
                return {'resultList': {'result': [{'doi': PAPER['doi'], 'pmcid': 'PMC123'}]}}
            if params:
                suffix = '2' if params.get('continuation-token') else '1'
                token = '' if suffix == '2' else '<NextContinuationToken>page2</NextContinuationToken>'
                return f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Contents><Key>metadata/PMC123.{suffix}.json</Key></Contents>{token}</ListBucketResult>'.encode()
            return {'doi': PAPER['doi'], 'is_manuscript': url.endswith('.2.json'),
                    'pdf_url': 's3://pmc-oa-opendata/PMC123.1/PMC123.1.pdf?md5=abc', 'version': 1}
    results = download.pmc_cloud(PAPER, Net())
    assert len(results) == 2
    assert results[0]['version'] == 'publishedVersion' and results[1]['version'] == 'acceptedVersion'
    assert results[0]['url'].startswith('https://pmc-oa-opendata.s3.amazonaws.com/')


def test_host_links_before_resolvers_and_preprint_title(tmp_path, monkeypatch):
    def forbidden(*a): raise AssertionError('Host link already succeeded')
    monkeypatch.setattr(download, 'RESOLVERS', [('forbidden', forbidden)])
    class Net:
        def get(self, *a, **kw): return pdf_bytes()
    class Recorder(Client):
        def attach(self, key, path, title, library):
            assert title.endswith('[预印本]')
            return super().attach(key, path, title, library)
    paper = {**PAPER, 'verified_pdf_links': [{'url': 'https://repo.test/p.pdf', 'version': 'preprint', 'source': 'https://repo.test/p'}]}
    assert download.download_pdf(paper, tmp_path, Recorder(), Net(), fallback_only=True)['status'] == 'downloaded'


def test_resume_unattached_file_needs_no_network(tmp_path):
    class Interrupted(Client):
        def attach(self, *a): raise TimeoutError('before commit')
    class Net:
        def get(self, *a, **kw): return pdf_bytes()
    with pytest.raises(TimeoutError): download.download_pdf(PAPER, tmp_path, Interrupted(), Net())
    assert download.download_pdf(PAPER, tmp_path, Client(), None)['status'] == 'downloaded'


def test_scihub_skips_bot_pages_and_parses_embed(tmp_path, monkeypatch):
    monkeypatch.setattr(download, 'scihub_mirrors', lambda net: ['https://sci-hub.se/', 'https://sci-hub.st/', 'https://sci-hub.ru/'])
    pages = {
        'https://sci-hub.se/10.1234/test': '<title>проверка на робота</title>',
        'https://sci-hub.st/10.1234/test': '<html><body>no article here</body></html>',
        'https://sci-hub.ru/10.1234/test': '<html><body><embed id="pdf" src="//http://cdn.test/p.pdf"></body></html>',
    }
    class Net:
        last_response_url = None
        def get(self, url, **kwargs):
            assert kwargs.get('cache') is False and kwargs.get('json_data') is False
            content = pages[url]
            return b'%PDF-1.4 x' if not content else content.encode()
    assert download.scihub(PAPER, Net()) == [{'url': 'https://cdn.test/p.pdf', 'source': 'Sci-Hub sci-hub.ru'}]


def test_scihub_last_resort_after_all_resolvers_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(download, 'RESOLVERS', [('scihub', download.scihub)])
    monkeypatch.setattr(download, 'scihub_mirrors', lambda net: ['https://sci-hub.se/', 'https://sci-hub.st/'])
    class Net:
        last_response_url = 'https://sci-hub.ren/10.1234/test'
        def get(self, url, **kwargs):
            if url.startswith('https://sci-hub.se/'):
                return b'<title>Verification - Sci-Hub</title>'
            if url.startswith('https://cdn.test/'):
                return pdf_bytes()
            mirror = url.removeprefix('https://sci-hub.st/')
            return (f'<html><body><iframe id="pdf" src="https://cdn.test/{mirror}.pdf#view=FitH"></iframe></body></html>').encode()
    paper = {**PAPER, 'pdf_urls': []}
    result = download.download_pdf(paper, tmp_path, Client(), Net())
    assert result['status'] == 'downloaded'
    assert result['source']['provider'] == 'scihub' and result['source']['url'] == 'https://cdn.test/10.1234/test.pdf#view=FitH' and result['source']['source'] == 'Sci-Hub sci-hub.st'
    assert download.normalized_doi('https://doi.org/10.1234/test') == '10.1234/test'


def test_scihub_mirrors_from_source_page_and_static_fallback():
    class Net:
        def __init__(self, content): self.content = content
        def get(self, url, **kwargs):
            assert url == download.SCIHUB_SOURCE
            return self.content.encode()
    page = '<a href="http://sci-hub.se">x</a> <a href="https://www.sci-hub.st/">y</a> <a href="https://scihub.bban.top/">z</a> <a href="https://elsewhere.test/">no</a>'
    assert download.scihub_mirrors(Net(page)) == ['https://sci-hub.se/', 'https://sci-hub.st/', 'https://scihub.bban.top/']
    assert download.scihub_mirrors(Net('<a href="https://elsewhere.test/">no</a>')) == download.SCIHUB_MIRRORS
    class Down:  # source-page outage falls back to the hardcoded list
        def get(self, *a, **k): raise ConnectionError
    assert download.scihub_mirrors(Down()) == download.SCIHUB_MIRRORS
