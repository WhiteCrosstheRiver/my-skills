import json

import httpx
import pytest

from zotero_skills.core import Run, read_json, write_json
from zotero_skills.cli import parser, execute
from zotero_skills.research import coverage, completion_status, load_plan, screening_batch
from zotero_skills.search import Providers, discover, merge_candidates, prepare_selected, snowball
from zotero_skills.review import prepare, build, audit_hash
from test_review import source, draft
from test_download import Client, pdf_bytes
from zotero_skills import download


def test_domain_only_requests_host_plan_and_resume_runs_all_facets(tmp_path, monkeypatch):
    result = execute(parser().parse_args(['--output', str(tmp_path), 'deep-search', '--topic', '电解液势函数', '--providers', 'crossref', '--citation-hops', '0']))
    assert result['status'] == 'awaiting_query_plan'
    plan = read_json(result['plan'])
    plan['facets'] = [{'name': '液体结构', 'queries': ['electrolyte machine learning potential']},
                      {'name': '输运', 'queries': ['neural potential ionic conductivity']}]
    write_json(result['plan'], plan)
    calls = []
    def query(self, q, limit, years):
        calls.append(q)
        return [{'title': q, 'sources': [{'provider': 'crossref', 'query': q}]}]
    monkeypatch.setattr(Providers, 'crossref', query)
    resumed = execute(parser().parse_args(['--output', str(tmp_path), 'resume', '--run', result['run'], '--plan', result['plan'], '--discover']))
    assert resumed['candidates'] == 2 and len(calls) == 2
    report = read_json(Run(result['run']).path / 'coverage.json')
    assert [f['retrieved'] for f in report['facets']] == [1, 1]
    execute(parser().parse_args(['--output', str(tmp_path), 'resume', '--run', result['run'], '--query', 'polarizable force fields']))
    assert len(calls) == 3
    execute(parser().parse_args(['--output', str(tmp_path), 'resume', '--run', result['run'], '--discover']))
    assert len(calls) == 3  # successfully completed tasks are not re-run


def test_empty_plan_is_not_executable(tmp_path):
    path = tmp_path / 'plan.json'
    write_json(path, {'facets': [{'name': 'concepts', 'queries': []}]})
    with pytest.raises(ValueError, match='nonempty'):
        load_plan(path)


def test_screening_batches_preserve_decisions_and_full_abstracts(tmp_path):
    run = Run.create(tmp_path, 'deep-search', {'topic': 'test'})
    abstract = 'Not a truncated abstract. ' * 100
    run.state['candidates'] = [{'id': str(i), 'title': str(i), 'abstract': abstract} for i in range(3)]
    result = screening_batch(run, 1)
    assert read_json(result['batch'])[0]['abstract'] == abstract
    path = tmp_path / 'batch-decisions.json'
    write_json(path, {'excluded': [{'id': '0', 'reason': 'Different field'}]})
    result = screening_batch(run, 1, path)
    assert result['unassessed'] == 2 and read_json(result['batch'])[0]['id'] == '1'
    write_json(path, {'included': [{'id': '1', 'reason': 'Relevant method', 'core': True}]})
    screening_batch(run, 1, path)
    saved = read_json(run.path / 'selection.json')
    assert len(saved['excluded']) == len(saved['included']) == 1
    assert run.state['papers'] == []


def test_candidate_id_survives_doi_enrichment():
    original = merge_candidates([{'title': 'Paper', 'year': 2025}])[0]
    enriched = merge_candidates([original, {'title': 'Paper', 'year': 2025, 'doi': '10.1/new'}])[0]
    assert enriched['doi'] == '10.1/new' and enriched['id'] == original['id']


def test_deep_note_cannot_only_cite_abstract_when_pdf_available():
    from test_search_notes import evidence, valid_note
    from zotero_skills.notes import validate_note
    e = evidence()
    note, claims = valid_note(e)
    claims[0]['evidence'] = [{'source': 'abstract', 'excerpt': 'abstract with a clear limitation'}]
    with pytest.raises(ValueError, match='Deep notes must cite'):
        validate_note(note, claims, e)


def test_583_candidates_19_selected_is_not_complete(tmp_path):
    run = Run.create(tmp_path, 'deep-search', {'topic': 'electrolyte'})
    run.state['candidates'] = [{'id': str(i), 'title': str(i)} for i in range(583)]
    run.state['papers'] = [{'id': str(i), 'title': str(i), 'status': 'published'} for i in range(19)]
    report = coverage(run)
    assert report['screening']['unassessed'] == 564
    assert completion_status(run) == 'selected_complete_scope_pending'
    write_json(run.path / 'selection.json', {'excluded': [{'id': str(i), 'reason': 'individually screened off-topic fixture'} for i in range(19, 583)]})
    assert completion_status(run) == 'complete'


def test_failed_queries_retry_without_discarding_other_provider_results(tmp_path, monkeypatch):
    run = Run.create(tmp_path, 'deep-search', {'topic': 'topic', 'queries': ['one', 'two'], 'providers': ['crossref'], 'candidate_limit': 2})
    failed = True
    def query(self, q, *args):
        if q == 'two' and failed:
            raise httpx.ReadTimeout('private request URL')
        return [{'title': q, 'sources': [{'provider': 'crossref', 'query': q}]}]
    monkeypatch.setattr(Providers, 'crossref', query)
    discover(run, None)
    assert len(run.state['candidates']) == 1
    assert coverage(run)['tasks'][1]['status'] == 'failed'
    failed = False
    discover(run, None)
    assert len(run.state['candidates']) == 2
    assert all(t['status'] == 'completed' for t in coverage(run)['tasks'])


def test_rate_limited_relevance_falls_back_to_bulk_with_provenance():
    class Net:
        def get(self, url, params, **kwargs):
            if not url.endswith('/bulk'):
                raise httpx.HTTPStatusError('429', request=httpx.Request('GET', url), response=httpx.Response(429))
            assert 'sort' not in params
            return {'data': [{'title': 'A relevant paper', 'externalIds': {'DOI': '10.1/a'}}]}
    result = Providers(Net()).semantic('electrolyte', 20)
    assert len(result) == 1 and result[0]['sources'][0]['endpoint'] == 'bulk'


def test_citations_page_beyond_100_and_send_api_key(monkeypatch):
    monkeypatch.setenv('SEMANTIC_SCHOLAR_API_KEY', 'test-key')
    class Net:
        def get(self, url, params, headers):
            assert headers == {'x-api-key': 'test-key'}
            offset, size = params['offset'], params['limit']
            return {'data': [{'citedPaper': {'title': f'Paper {n}'}} for n in range(offset, offset + size)], 'next': offset + size}
    assert len(Providers(Net()).citations({'doi': '10.1/a'}, limit=151, directions=('references',))) == 151


def test_snowball_checkpoints_directions_and_retries_failures(tmp_path, monkeypatch):
    run = Run.create(tmp_path, 'deep-search', {'topic': 'electrolyte', 'citation_seeds': 1})
    run.state['candidates'] = merge_candidates([{'title': 'electrolyte', 'doi': '10.1/seed'}])
    calls = []
    def citations(self, seed, limit, directions):
        direction = directions[0]
        calls.append(direction)
        if direction == 'citations' and calls.count(direction) == 1:
            raise RuntimeError('unavailable')
        return [{'title': direction, 'doi': '10.1/' + direction}]
    monkeypatch.setattr(Providers, 'citations', citations)
    snowball(run, None)
    snowball(run, None)
    assert calls == ['references', 'citations', 'citations']
    assert len(run.state['candidates']) == 3


def test_incremental_selection_cannot_silently_drop_existing_papers(tmp_path):
    run = Run.create(tmp_path, 'deep-search', {'limit': 10})
    run.state['candidates'] = [{'id': 'old', 'title': 'Old'}, {'id': 'new', 'title': 'New'}]
    run.state['papers'] = [{'id': 'old', 'title': 'Old', 'status': 'published'}]
    path = tmp_path / 'selection.json'
    write_json(path, {'included': [{'id': 'new', 'reason': 'relevant'}]})
    with pytest.raises(ValueError, match='retain earlier'):
        prepare_selected(run, None, None, path)
    write_json(path, {'included': [{'id': 'old', 'reason': 'relevant'}], 'excluded': [{'id': 'old', 'reason': 'conflict'}]})
    with pytest.raises(ValueError, match='conflicting'):
        prepare_selected(run, None, None, path)


def test_article_landing_page_download_without_doi(tmp_path, monkeypatch):
    monkeypatch.setattr(download, 'RESOLVERS', [])
    class Net:
        def get(self, url, **kwargs):
            return (b'<meta name="citation_title" content="A paper"><meta name="citation_pdf_url" content="/paper.pdf">'
                    if url.endswith('/article') else pdf_bytes())
    result = download.download_pdf({'title': 'A paper', 'item_key': 'ITEM0001', 'url': 'https://author.test/article'}, tmp_path, Client(), Net())
    assert result['status'] == 'downloaded'
    assert result['source']['url'] == 'https://author.test/paper.pdf'


def test_preprint_doi_is_tried_after_journal_resolvers(tmp_path, monkeypatch):
    seen = []
    def resolver(p, net):
        seen.append(p['doi'])
        return [{'url': 'https://repo.test/p.pdf'}] if p['doi'] == '10.1/preprint' else []
    monkeypatch.setattr(download, 'RESOLVERS', [('repo', resolver)])
    class Net:
        def get(self, *args, **kwargs): return pdf_bytes()
    result = download.download_pdf({'title': 'Paper', 'item_key': 'ITEM0001', 'doi': '10.1/journal', 'preprint_doi': '10.1/preprint'}, tmp_path, Client(), Net())
    assert seen == ['10.1/journal', '10.1/preprint']
    assert result['source']['version'] == 'preprint'


def test_review_carries_unassessed_and_unpublished_scope_into_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv('ZOTERO_SKILLS_REVIEW_DEST', str(tmp_path / 'unused'))
    s = source(tmp_path)
    s.state['candidates'] = [{'id': 'TEST0001', 'title': 'Published'}, {'id': 'pending', 'title': 'Unscreened'}]
    s.state['papers'].append({'id': 'missing', 'title': 'Selected but unread', 'item_key': 'MISSING1', 'status': 'awaiting_analysis'})
    s.save()
    run = Run(prepare(tmp_path, 'Evidence scope', [s.path])['run'])
    assert run.state['scope']['scope_incomplete']
    assert len(read_json(run.path / 'evidence-cards.json')) == 1
    draft(run, ['TEST0001'])
    result = build(run)
    from pathlib import Path
    version = Path(result['version'])
    text = (version / 'review.md').read_text(encoding='utf-8')
    assert '1 未筛选' in text and '1 篇尚无' in text and '阶段性综述' in text
    assert '阶段性综述' in (version / 'review.html').read_text(encoding='utf-8')
    old_hash = audit_hash(run)
    run.state['scope']['included_notes'] = 100
    assert audit_hash(run) != old_hash  # coverage cannot change behind the review audit
