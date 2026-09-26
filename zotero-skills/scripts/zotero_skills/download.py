"""Lazy PDF fallback and additive, resumable backfill of existing Zotero items."""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

import pymupdf

from .core import MCP, Network, Run, digest, lock, now, read_json, write_json, write_lock_path


def normalized_doi(value):
    return re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', str(value or '').strip(), flags=re.I).lower()


def local_pdfs(snapshot):
    # A scan or encrypted local PDF still belongs to the user: never replace it.
    return [a for a in snapshot['attachments'] if
            (a.get('contentType') == 'application/pdf' or str(a.get('path', '')).lower().endswith('.pdf'))
            and a.get('path') and Path(a['path']).is_file()]


def valid_pdf(path):
    with Path(path).open('rb') as file:
        if b'%PDF-' not in file.read(1024):
            raise ValueError('Response is not a PDF')
    with pymupdf.open(path) as doc:
        if doc.is_encrypted or doc.page_count < 1:
            raise ValueError('Encrypted or empty PDF')
        return doc.page_count


def failure(exc):
    # Request exceptions can contain API credentials in query strings.
    response = getattr(exc, 'response', None)
    return type(exc).__name__ + (f' HTTP {response.status_code}' if response is not None else '')


def openalex(paper, net):
    ident = normalized_doi(paper.get('doi'))
    if not ident:
        return []
    params = {'api_key': os.environ['OPENALEX_API_KEY']} if os.environ.get('OPENALEX_API_KEY') else {}
    data = net.get('https://api.openalex.org/works/doi:' + quote(ident, safe='/'), params)
    if data.get('doi') and normalized_doi(data['doi']) != ident:
        raise ValueError('Resolver DOI mismatch')
    out = []
    for loc in [data.get('best_oa_location') or {}] + (data.get('locations') or []):
        if loc.get('is_oa') is True:
            for field in ('pdf_url', 'landing_page_url'):
                if loc.get(field):
                    out.append({'url': loc[field], 'version': loc.get('version'), 'license': loc.get('license')})
    return out


def unpaywall(paper, net):
    ident = normalized_doi(paper.get('doi'))
    if not ident:
        return []
    email = os.environ.get('UNPAYWALL_EMAIL') or os.environ.get('ZOTERO_SKILLS_CONTACT_EMAIL')
    if not email:
        raise LookupError('UNPAYWALL_EMAIL not configured')
    data = net.get('https://api.unpaywall.org/v2/' + quote(ident, safe='/'), {'email': email})
    if normalized_doi(data.get('doi')) != ident:
        raise ValueError('Resolver DOI mismatch')
    return [{'url': loc.get('url_for_pdf') or loc.get('url_for_landing_page'),
             'version': loc.get('version'), 'license': loc.get('license')}
            for loc in data.get('oa_locations', []) if loc.get('url_for_pdf') or loc.get('url_for_landing_page')]


def semantic(paper, net):
    ident = normalized_doi(paper.get('doi'))
    if not ident:
        return []
    headers = {'x-api-key': os.environ['SEMANTIC_SCHOLAR_API_KEY']} if os.environ.get('SEMANTIC_SCHOLAR_API_KEY') else None
    data = net.get('https://api.semanticscholar.org/graph/v1/paper/DOI:' + quote(ident, safe='/'),
                   {'fields': 'title,externalIds,openAccessPdf'}, headers=headers)
    ids = data.get('externalIds') or {}
    if ids.get('DOI') and normalized_doi(ids['DOI']) != ident:
        raise ValueError('Resolver DOI mismatch')
    out = [{'url': data['openAccessPdf']['url']}] if (data.get('openAccessPdf') or {}).get('url') else []
    if ids.get('ArXiv'):
        out.append({'url': 'https://arxiv.org/pdf/' + ids['ArXiv'], 'version': 'preprint'})
    return out


def europepmc(paper, net):
    ident = normalized_doi(paper.get('doi'))
    if not ident:
        return []
    data = net.get('https://www.ebi.ac.uk/europepmc/webservices/rest/search',
                   {'query': f'DOI:"{ident}"', 'format': 'json', 'resultType': 'core', 'pageSize': 10})
    return [{'url': u['url']} for row in data.get('resultList', {}).get('result', [])
            if normalized_doi(row.get('doi')) == ident
            for u in row.get('fullTextUrlList', {}).get('fullTextUrl', [])
            if str(u.get('documentStyle')).lower() == 'pdf' and u.get('availabilityCode') == 'OA']


def crossref(paper, net):
    ident = normalized_doi(paper.get('doi'))
    if not ident:
        return []
    data = net.get('https://api.crossref.org/works/' + quote(ident, safe='/'))['message']
    if normalized_doi(data.get('DOI')) != ident:
        raise ValueError('Resolver DOI mismatch')
    # These are publisher-supplied endpoints; an entitlement failure stays a failure.
    return [{'url': x['URL']} for x in data.get('link', []) if x.get('content-type') == 'application/pdf'] + [{'url': 'https://doi.org/' + ident}]


def pmc_cloud(paper, net):
    """Current PMC article datasets (the legacy OA/FTP service retired August 2026)."""
    ident = normalized_doi(paper.get('doi'))
    if not ident:
        return []
    data = net.get('https://www.ebi.ac.uk/europepmc/webservices/rest/search',
                   {'query': f'DOI:"{ident}"', 'format': 'json', 'resultType': 'core', 'pageSize': 10})
    ids = {r['pmcid'] for r in data.get('resultList', {}).get('result', [])
           if normalized_doi(r.get('doi')) == ident and re.fullmatch(r'PMC\d+', r.get('pmcid', ''))}
    base, out = 'https://pmc-oa-opendata.s3.amazonaws.com/', []
    for pmcid in sorted(ids):
        token = None
        while True:
            params = {'list-type': 2, 'prefix': 'metadata/' + pmcid + '.', 'max-keys': 100}
            if token:
                params['continuation-token'] = token
            root = ET.fromstring(net.get(base, params, json_data=False))
            for element in root.findall('{*}Contents/{*}Key'):
                key = element.text
                if not re.fullmatch(r'metadata/' + pmcid + r'\.\d+\.json', key or ''):
                    continue
                meta = net.get(base + key)
                if normalized_doi(meta.get('doi')) != ident or not meta.get('pdf_url'):
                    continue
                url = meta['pdf_url'].replace('s3://pmc-oa-opendata/', base)
                if urlsplit(url).hostname != 'pmc-oa-opendata.s3.amazonaws.com':
                    continue
                out.append({'url': url, 'version': 'acceptedVersion' if meta.get('is_manuscript') in (True, 'yes') else 'publishedVersion',
                            'license': meta.get('license_code'), 'pmcid': pmcid, 'pmc_version': meta.get('version'),
                            'source': 'NIH NLM NCBI PubMed Central Article Datasets'})
            next_token = root.findtext('{*}NextContinuationToken')
            if not next_token or next_token == token:
                break
            token = next_token
    return sorted(out, key=lambda row: row['version'] != 'publishedVersion')


RESOLVERS = [('openalex', openalex), ('unpaywall', unpaywall), ('semantic', semantic),
             ('europepmc', europepmc), ('pmc-cloud', pmc_cloud), ('crossref', crossref)]


class CitationMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            name = (attrs.get('name') or attrs.get('property') or '').lower()
            self.values.setdefault(name, []).append(attrs.get('content', ''))


def page_links(content, url, paper):
    parser = CitationMeta()
    parser.feed(content.decode('utf-8', errors='replace'))
    meta = parser.values
    dois = meta.get('citation_doi', []) + meta.get('dc.identifier', [])
    ident = normalized_doi(paper.get('doi'))
    norm = lambda s: re.sub(r'[^\w]', '', s.casefold())
    title_match = any(norm(t) == norm(paper['title']) for t in meta.get('citation_title', []))
    if not ((ident and any(normalized_doi(d) == ident for d in dois)) or title_match):
        return []
    return [urljoin(url, value) for value in meta.get('citation_pdf_url', []) if value]


def download_pdf(paper, directory, mcp, net, library=1, snapshot=None, fallback_only=False, resolvers=None, check_library=False):
    """Return on first success. Attach errors stop: a timed-out write may have committed."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    report_path = directory / 'pdf-download.json'
    report = read_json(report_path) if report_path.exists() else {'attempts': []}
    report.update(item_key=paper['item_key'], checked_at=now())
    snap = snapshot if snapshot is not None else mcp.snapshot(paper['item_key'], library)
    existing = local_pdfs(snap)
    if not existing and check_library:
        existing = mcp.find_local_pdfs(paper, library)
    if existing:
        # No resolver calls, hashing, parsing, writing or changes to the user's files.
        report.update(status='skipped_existing', attachment_keys=[a['key'] for a in existing],
                      parent_keys=list(dict.fromkeys(a.get('parent_key', paper['item_key']) for a in existing)))
        write_json(report_path, report)
        return report

    path = directory / 'downloaded.pdf'
    def attach():
        report.update(status='attaching', path=str(path), sha256=digest(path.read_bytes()))
        write_json(report_path, report)  # recover after interruption using this same file
        version = (report.get('source') or {}).get('version')
        title = paper['title'] + (' [预印本]' if version in ('preprint', 'submittedVersion') else '')
        result = mcp.attach(paper['item_key'], path, title, library)
        after = mcp.snapshot(paper['item_key'], library)
        attached = next((a for a in local_pdfs(after) if a['key'] == result['key']), None)
        if not attached or digest(Path(attached['path']).read_bytes()) != report['sha256']:
            raise RuntimeError('PDF attachment readback failed')
        report.update(status='downloaded', attachment_key=result['key'], completed_at=now())
        write_json(report_path, report)
        return report

    if path.exists() and report.get('sha256') == digest(path.read_bytes()):
        valid_pdf(path)
        return attach()

    seen = set()
    def attempt(candidate, provider, depth=0):
        url = candidate.get('url')
        if not url or url in seen or urlsplit(url).scheme not in ('http', 'https'):
            return False
        seen.add(url)
        record = {'provider': provider, **candidate, 'at': now()}
        report['attempts'].append(record)
        try:
            content = net.get(url, json_data=False, cache=False)
            if b'%PDF-' not in content[:1024]:
                links = page_links(content, getattr(net, 'last_response_url', url), paper)
                record['status'] = 'html_with_pdf_link' if links else 'not_pdf'
                write_json(report_path, report)
                # Only declared article PDF metadata, no recursive link crawling.
                for link in links[:3] if depth == 0 else []:
                    if attempt({'url': link, 'landing_page': url}, provider + ':citation_pdf', depth=1):
                        return True
                return False
            temp = directory / 'download.part'
            temp.write_bytes(content)
            record['pages'] = valid_pdf(temp)
            temp.replace(path)
            record['status'] = 'downloaded'
            report.update(source=record, sha256=digest(content))
            write_json(report_path, report)
            return True
        except Exception as exc:
            record.update(status='failed', reason=failure(exc))
            write_json(report_path, report)
            return False

    if not fallback_only:
        urls = list(paper.get('pdf_urls') or [])
        arxiv = paper.get('arxiv')
        if not arxiv and normalized_doi(paper.get('doi')).startswith('10.48550/arxiv.'):
            arxiv = normalized_doi(paper['doi']).split('arxiv.', 1)[1]
        if arxiv:
            urls.append('https://arxiv.org/pdf/' + arxiv)
        for url in urls:
            if attempt({'url': url}, 'primary'):
                return attach()
    for candidate in paper.get('verified_pdf_links', []):
        if attempt(candidate, 'host-verified'):
            return attach()
    for name, resolve in RESOLVERS:
        if resolvers is not None and name not in resolvers:
            continue
        try:
            candidates = resolve(paper, net)
            report['attempts'].append({'provider': name, 'stage': 'resolve', 'status': 'resolved', 'count': len(candidates), 'at': now()})
        except Exception as exc:
            report['attempts'].append({'provider': name, 'stage': 'resolve', 'status': 'unconfigured' if isinstance(exc, LookupError) else 'failed', 'reason': failure(exc), 'at': now()})
            candidates = []
        write_json(report_path, report)
        for candidate in candidates:
            if attempt(candidate, name):
                return attach()
    report.update(status='unavailable')
    write_json(report_path, report)
    return report


def register(sub):
    command = sub.add_parser('fetch-pdfs', help='Add only missing PDFs to selected items; preserve notes and evidence')
    command.add_argument('--run', type=Path, action='append', required=True)
    command.add_argument('--fallback-only', action='store_true', help='Skip the original provider URLs')
    command.add_argument('--links', type=Path, help='Host-verified JSON list: item_key, url, source, version')
    command.add_argument('--resolvers', nargs='+', choices=[name for name, _ in RESOLVERS], help='Test or retry selected fallback sources only')


def execute(args):
    mcp, net = MCP(args.url), Network(args.output / 'cache')
    results, seen = [], {}
    links = read_json(args.links) if args.links else []
    if not isinstance(links, list) or any(not all(row.get(k) for k in ('item_key', 'url', 'source', 'version')) for row in links):
        raise ValueError('Each verified link requires item_key, url, source, version')
    known = {p.get('item_key') for path in args.run for p in Run(path).state['papers']}
    if any(row['item_key'] not in known for row in links):
        raise ValueError('Verified link item is outside the selected runs')
    with lock(write_lock_path()):
        for path in args.run:
            run = Run(path)
            if run.state['mode'] not in ('deep-search', 'distill'):
                raise ValueError('fetch-pdfs requires a deep-search or distill run')
            with lock(run.path / '.lock'):
                for paper in run.state['papers']:
                    if not paper.get('item_key'):
                        continue
                    key = (run.state['config'].get('library', 1), paper['item_key'])
                    if key in seen:
                        result = seen[key]
                    else:
                        # An uncertain Zotero write aborts the batch. Re-run checks actual files first.
                        candidate = {**paper, 'verified_pdf_links': [row for row in links if row['item_key'] == key[1]]}
                        result = download_pdf(candidate, run.paper_dir(paper), mcp, net, key[0], fallback_only=args.fallback_only, resolvers=args.resolvers, check_library=True)
                        seen[key] = result
                        results.append({'item_key': key[1], 'title': paper['title'], **result})
                    if result['status'] == 'downloaded':
                        paper['pdf_attachment_key'] = result['attachment_key']
                        paper['evidence_refresh_required'] = True
                        run.save()
    output = args.output / 'downloads' / ('backfill-' + now().replace(':', '-') + '.json')
    write_json(output, results)
    return {'report': str(output), 'unique_items': len(results),
            'counts': {s: sum(r['status'] == s for r in results) for s in ('downloaded', 'skipped_existing', 'unavailable')}}
