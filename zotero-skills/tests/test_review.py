import json
from pathlib import Path

import pytest

from zotero_skills.core import Run, digest, now, read_json, write_json
from zotero_skills.review import prepare, validate, build, render_body, audit_hash
from test_search_notes import evidence, valid_note


def source(output, key='TEST0001'):
    run = Run.create(output, 'distill', {'library': 1})
    paper = {'id': key, 'item_key': key, 'title': 'Synthetic test', 'status': 'published'}
    run.state['papers'] = [paper]; run.save()
    directory = run.paper_dir(paper)
    e = evidence(); e['item_key'] = key
    note, claims = valid_note(e)
    (directory / 'note.md').write_text(note, encoding='utf-8')
    write_json(directory / 'evidence.json', e)
    write_json(directory / 'claims.json', claims)
    write_json(directory / 'publication.json', {'item_key': key, 'library_id': 1, 'published_at': now(), 'content_hash': digest(note), 'claims': claims, 'evidence_hash': digest(json.dumps(e, ensure_ascii=False, sort_keys=True))})
    return run


def draft(run, keys):
    text = '# 测试综述\n\n## 有边界的结论\n\n这是合成测试结果，20%仅是原始测试句的值，不是实际论文。[R1]\n\n$$E = \\sum_{i=1}^{N} E_i$$\n'
    (run.path / 'review.md').write_text(text, encoding='utf-8')
    write_json(run.path / 'review-claims.json', [{'id': 'R1', 'statement': '合成测试结果', 'kind': 'reported', 'refs': [k + ':C1' for k in keys]}])
    write_json(run.path / 'audit.json', {'status': 'passed', 'draft_hash': digest(text), 'review_hash': audit_hash(run), 'reviewer': 'Synthetic fixture audit', 'checks': ['Fixture identities and source excerpt']})


def test_versions_citations_and_tamper_rejection(tmp_path):
    s = source(tmp_path)
    first = Run(prepare(tmp_path, '中文路径综述', [s.path])['run']); draft(first, ['TEST0001'])
    a = build(first); old = Path(a['version']); old_hash = digest((old / 'review.html').read_bytes())
    assert build(first)['reused']
    assert '$$E = \\sum_{i=1}^{N} E_i$$' in (old / 'review.html').read_text(encoding='utf-8')
    assert '(#r1)' in (old / 'review.md').read_text(encoding='utf-8')
    assert (old / 'katex/contrib/auto-render.min.js').is_file()
    s2 = source(tmp_path, 'TEST0002')
    second = Run(prepare(tmp_path, '中文路径综述', [s.path, s2.path])['run']); draft(second, ['TEST0001', 'TEST0002'])
    b = build(second)
    assert b['changes']['added_papers'] == ['TEST0002']
    assert b['version'] != a['version'] and digest((old / 'review.html').read_bytes()) == old_hash
    c = read_json(second.path / 'review-claims.json'); c[0]['refs'].append('FAKE:C1');write_json(second.path / 'review-claims.json', c)
    with pytest.raises(ValueError, match='Unknown source'): validate(second)
    c[0]['refs'].pop();write_json(second.path / 'review-claims.json', c)
    (second.path / 'sources/TEST0001/note.md').write_text('tampered', encoding='utf-8')
    with pytest.raises(ValueError, match='Frozen note'): validate(second)


def test_math_survives_markdown_parser():
    formula = r'$$\sigma_{f,i}=\sqrt{\frac{1}{M}\sum_m |F_i^m-\bar F_i|^2}$$'
    rendered = render_body(formula)
    assert formula in rendered and '<em>' not in rendered


def test_recovery_and_audit_binding(tmp_path, monkeypatch):
    s = source(tmp_path)
    run = Run(prepare(tmp_path, '恢复测试', [s.path])['run']); draft(run, ['TEST0001'])
    original = run.save
    monkeypatch.setattr(run, 'save', lambda: (_ for _ in ()).throw(KeyboardInterrupt('after rename')))
    with pytest.raises(KeyboardInterrupt): build(run)
    monkeypatch.setattr(run, 'save', original)
    run = Run(run.path)
    recovered = build(run)
    assert recovered['reused']
    assert len(list((tmp_path / 'reviews').glob('*/*/manifest.json'))) == 1
    text = (run.path / 'review.md').read_text(encoding='utf-8') + '\n新增推断边界。[R1]\n'
    (run.path / 'review.md').write_text(text, encoding='utf-8')
    with pytest.raises(ValueError, match='audit'): build(run)
    write_json(run.path / 'audit.json', {'status': 'passed', 'draft_hash': digest(text), 'review_hash': audit_hash(run), 'reviewer': 'Fixture audit', 'checks': ['Rechecked revision']})
    updated = build(run)
    assert updated['version'] != recovered['version']
    claims = read_json(run.path / 'review-claims.json'); claims[0]['kind'] = 'synthesis';write_json(run.path / 'review-claims.json', claims)
    with pytest.raises(ValueError, match='audit'): build(run)


def test_unpublished_claim_edits_are_rejected(tmp_path):
    s = source(tmp_path); path = s.paper_dir(s.state['papers'][0]) / 'claims.json'
    claims = read_json(path);claims[0]['statement'] = 'A changed claim';write_json(path, claims)
    with pytest.raises(ValueError, match='Published claims changed'): prepare(tmp_path, 'test', [s.path])
