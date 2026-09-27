"""Host-written synthesis, grounded citations, offline rendering and immutable versions."""
import csv
from collections import Counter
import html
import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .core import write_lock_path
from .core import MCP, Run, digest, lock, now, read_json, write_json
from .library import enumerate_items
from .notes import MD, split_frontmatter, validate_note
from .research import screening_summary

ASSETS = Path(__file__).parent / 'assets'
CITATION = re.compile(r'\[(R\d+)\]')


def render_body(text):
    # Keep LaTeX out of the Markdown emphasis/escape parser.
    formulas = []
    def save(match):
        formulas.append(match[0])
        return 'ZOTEROMATHPLACE' + str(len(formulas) - 1) + 'END'
    result = MD.render(re.sub(r'\$\$[\s\S]*?\$\$|\$[^\n$]+\$', save, text))
    return re.sub(r'ZOTEROMATHPLACE(\d+)END', lambda m: html.escape(formulas[int(m[1])]), result)


# Which note section feeds each matrix column, per note depth. Stubs only contribute a line
# to the review's reading-list appendix; they are never narrated as if they were findings.
MATRIX_FIELDS = {
    'legacy': {'takeaway': '核心贡献', 'question': '背景与研究问题', 'method': '关键方法与过程', 'results': '结果与对照', 'conflicts': '局限与矛盾'},
    'deep': {'takeaway': '一句话结论', 'question': '问题与动机', 'method': '方法要点', 'results': '关键结果', 'conflicts': '边界与疑点'},
    'brief': {'takeaway': '一句话结论', 'question': '', 'method': '方法定位', 'results': '作者声称', 'conflicts': '可信度与待核'},
    'stub': {'takeaway': '一句话定位', 'question': '', 'method': '', 'results': '', 'conflicts': ''},
}


def section(body, heading):
    match = re.search(r'^##\s+' + re.escape(heading) + r'\s*\n(.*?)(?=^##\s|\Z)', body, re.M | re.S)
    return match[1].strip() if match else ''


def prepare(output, title, source_runs=(), collection=None, topic=None, library=1, mcp=None):
    publications = {}
    scope_runs, unpublished = [], []
    for source in source_runs:
        run = Run(source)
        scope_runs.append({'run': str(run.path), **screening_summary(run),
                           'selected': len(run.state['papers']), 'status': run.state['status'],
                           'host_pending': sum(s.get('status', 'pending') == 'pending' for s in run.state.get('host_searches', [])),
                           'failed_queries': sum(t['status'] == 'failed' for t in run.state.get('search_tasks', {}).values()),
                           'failed_citation_tasks': sum(t['status'] == 'failed' for t in run.state.get('citation_tasks', {}).values())})
        for paper in run.state['papers']:
            path = run.paper_dir(paper) / 'publication.json'
            if paper['status'] == 'published' and path.is_file():
                pub = read_json(path)
                key = str(pub['library_id']) + ':' + pub['item_key']
                previous = publications.get(key)
                if previous is None or pub['published_at'] > read_json(previous)['published_at']:
                    publications[key] = path
            else:
                unpublished.append({'key': paper.get('item_key'), 'title': paper['title'], 'status': paper['status']})
    if collection or topic:
        for item in enumerate_items(mcp or MCP(), library, collection, topic):
            files = list((Path(output) / 'notes' / str(library) / item['key']).glob('*/publication.json'))
            if files:
                path = max(files, key=lambda p: read_json(p)['published_at'])
                publications[str(library) + ':' + item['key']] = path
            else:
                unpublished.append({'key': item['key'], 'title': item.get('title', ''), 'status': 'no_published_note'})
    if not publications:
        raise ValueError('No published, validated notes in the selected scope')
    libraries = {read_json(path)['library_id'] for path in publications.values()}
    if len(libraries) != 1 or library not in libraries:
        raise ValueError('Review inputs must belong to the selected library')
    run = Run.create(output, 'review', {'title': title, 'library': library, 'collection': collection, 'topic': topic})
    sources, matrix = [], []
    for identity, path in sorted(publications.items()):
        pub = read_json(path)
        directory = path.parent
        note = (directory / 'note.md').read_text(encoding='utf-8')
        claims, evidence = read_json(directory / 'claims.json'), read_json(directory / 'evidence.json')
        meta, body = validate_note(note, claims, evidence)
        if digest(note) != pub['content_hash']:
            raise ValueError('Published note has changed: republish before review')
        claims_hash = digest(json.dumps(claims, sort_keys=True, ensure_ascii=False))
        if (pub.get('claims_hash') and pub['claims_hash'] != claims_hash) or ('claims' in pub and pub['claims'] != claims):
            raise ValueError('Published claims changed: republish before review')
        if not pub.get('claims_hash') and 'claims' not in pub:
            raise ValueError('Publication lacks claims provenance; republish note')
        if digest(json.dumps(evidence, sort_keys=True, ensure_ascii=False)) != pub['evidence_hash']:
            raise ValueError('Published evidence changed: republish before review')
        key = pub['item_key']
        target = run.path / 'sources' / key
        target.mkdir(parents=True)
        for name in ['note.md', 'claims.json', 'evidence.json', 'publication.json']:
            shutil.copyfile(directory / name, target / name)
        entry = {'key': key, 'library_id': library, 'title': evidence['title'], 'doi': evidence.get('doi'), 'hash': pub['content_hash'], 'evidence_hash': pub['evidence_hash'], 'evidence_level': evidence['level'], 'claims': claims, 'note_path': 'sources/' + key + '/note.md'}
        entry['claims_hash'] = digest(json.dumps(claims, sort_keys=True, ensure_ascii=False))
        entry['version_hash'] = digest(entry['hash'] + entry['claims_hash'] + entry['evidence_hash'])
        sources.append(entry)
        tier = meta.get('note_tier', 'legacy')
        entry['note_tier'] = tier
        entry['fulltext_claims'] = sum(any(ref.get('page') and ref.get('source') not in ('abstract', 'metadata') for ref in c.get('evidence', [])) for c in claims)
        fields = MATRIX_FIELDS[tier]
        matrix.append({'key': key, 'title': entry['title'], 'tier': tier, 'strength': evidence['level'], 'date': evidence.get('metadata', {}).get('date', ''),
                       'venue': evidence.get('metadata', {}).get('publicationTitle', ''), **{name: section(body, heading) if heading else '' for name, heading in fields.items()},
                       'intuition': section(body, '核心思路'), 'connections': section(body, '关联与启发') or section(body, '研究启发'),
                       'reproducibility': section(body, '代码、数据与复现'), 'reading_scope': section(body, '证据索引') or section(body, '证据索引与生成记录'),
                       'claim_ids': [c['id'] for c in claims]})
    published_keys = {s['key'] for s in sources}
    unpublished = list({(p.get('key'), p['title']): p for p in unpublished if p.get('key') not in published_keys}.values())
    scope = {'source_runs': scope_runs, 'unpublished': unpublished,
             'included_notes': len(sources), 'tiers': dict(Counter(s['note_tier'] for s in sources)),
             'evidence': dict(Counter(s['evidence_level'] for s in sources)),
             'fulltext_without_page_claims': [s['key'] for s in sources if s['evidence_level'] == 'fulltext' and not s['fulltext_claims']],
             'scope_incomplete': bool(unpublished or any(r['unassessed'] or r['deferred'] or r['host_pending'] or r['failed_queries'] or r['failed_citation_tasks'] for r in scope_runs)),
             'discovery_scope_known': any(r['candidates'] for r in scope_runs)}
    run.state.update(sources=sources, scope=scope, status='awaiting_synthesis')
    run.save()
    write_json(run.path / 'matrix.json', matrix)
    write_json(run.path / 'review-scope.json', scope)
    # Complete claims and locators, not just matrix snippets. The host can group
    # these into arguments without losing qualifiers or primary-source pointers.
    write_json(run.path / 'evidence-cards.json', [
        {'ref': s['key'] + ':' + c['id'], 'title': s['title'], 'tier': s['note_tier'],
         'evidence_level': s['evidence_level'], 'claim': c, 'note': s['note_path']}
        for s in sources for c in s['claims']])
    (run.path / 'synthesis-workbook.md').write_text(
        '# 综述分析工作底稿（待作者完成）\n\n' + scope_disclosure(scope) +
        '\n\n先读 review-scope.json、matrix.json 与 evidence-cards.json。待筛/待读不能算作排除；重要分支证据不足时回到检索和精读。\n\n'
        '## 研究问题与读者路径\n\n逐个明确问题、读者需要的概念、回答该问题的章节、尚缺的证据。\n\n'
        '## 问题—证据地图\n\n| 问题 | 支持 claim refs | 反向/限定证据 | 适用条件 | 仍未知 |\n|---|---|---|---|---|\n\n'
        '## 可比性与分歧\n\n| 比较 | 对象/数据划分 | 指标/单位 | 条件/预算 | 可比程度 | 分歧的可能解释 |\n|---|---|---|---|---|---|\n\n'
        '## 从直觉到机制\n\n每个重要机制：为什么需要 → 最小例子 → 输入/步骤/输出 → 公式与符号 → 原文证据 → 失效边界。例子如为示意需明确标注。\n\n'
        '## 综合判断与下一步\n\n每条判断列出原始 claim refs、复现/互补/分歧/外推关系、假设、不能推出什么，以及能区分解释的下一项实验。\n', encoding='utf-8')
    with (run.path / 'matrix.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(matrix[0]))
        writer.writeheader(); writer.writerows(matrix)
    tiers = {t: sum(s['note_tier'] == t for s in sources) for t in ['deep', 'brief', 'stub', 'legacy']}
    return {'run': str(run.path), 'papers': len(sources), 'tiers': tiers, 'scope_incomplete': scope['scope_incomplete'],
            'scope': str(run.path / 'review-scope.json'), 'workbook': str(run.path / 'synthesis-workbook.md'), 'status': 'awaiting_synthesis',
            'next': 'Read review-scope.json first: unfinished screening/notes mean an interim subset, not domain completion. Fill synthesis-workbook.md from evidence-cards.json and full notes; deepen missing anchors. Write review.md and review-claims.json, then independently audit.'}


def scope_disclosure(scope):
    lines = [f"本版纳入 {scope['included_notes']} 篇已发布笔记；笔记深度：" + '、'.join(f'{k} {v}' for k, v in scope['tiers'].items()) + '。',
             '证据取得情况：' + '、'.join(f'{k} {v}' for k, v in scope['evidence'].items()) + '。笔记深度不等于全文取得情况。']
    for row in scope['source_runs']:
        if row['candidates']:
            lines.append(f"来源检索批次：{row['candidates']} 候选，{row['included']} 入选，{row['excluded']} 排除，{row['deferred']} 暂缓，{row['unassessed']} 未筛选。不同批次可能重叠，不相加为唯一文献数。")
        if row.get('host_pending') or row.get('failed_queries') or row.get('failed_citation_tasks'):
            lines.append(f"该批次还有 {row.get('host_pending', 0)} 个未完成浏览器检索、{row.get('failed_queries', 0)} 个失败检索、{row.get('failed_citation_tasks', 0)} 个失败引文任务。")
    if scope.get('fulltext_without_page_claims'):
        lines.append(f"{len(scope['fulltext_without_page_claims'])} 篇已取得全文的笔记没有页级声明引用，不能据此声称已完成全文精读。")
    if scope['unpublished']:
        lines.append(f"范围内另有 {len(scope['unpublished'])} 篇尚无可纳入的已发布笔记。")
    if scope['scope_incomplete']:
        lines.append('本版是部分证据的阶段性综述，尚不能声称完成该领域的全面梳理。')
    if not scope['discovery_scope_known']:
        lines.append('输入未包含原始检索范围；无法由已发布笔记数量推断领域覆盖率。')
    return '\n\n'.join(lines)


def validate(run):
    text = (run.path / 'review.md').read_text(encoding='utf-8')
    claims = read_json(run.path / 'review-claims.json')
    sources = {s['key']: s for s in run.state['sources']}
    lookup = {s['key'] + ':' + c['id']: c for s in sources.values() for c in s['claims']}
    for source in sources.values():
        path = run.path / source['note_path']
        if digest(path.read_text(encoding='utf-8')) != source['hash']:
            raise ValueError('Frozen note changed: ' + source['key'])
        e = read_json(path.parent / 'evidence.json')
        frozen_claims = read_json(path.parent / 'claims.json')
        if frozen_claims != source['claims']:
            raise ValueError('Frozen source claims changed')
        validate_note(path.read_text(encoding='utf-8'), frozen_claims, e)
        if digest(json.dumps(e, sort_keys=True, ensure_ascii=False)) != source['evidence_hash']:
            raise ValueError('Frozen evidence changed')
    ids = set()
    for claim in claims:
        cid = claim.get('id', '')
        if not re.fullmatch('R[0-9]+', cid) or cid in ids or '[' + cid + ']' not in text:
            raise ValueError('Missing/duplicate/unreferenced review claim: ' + cid)
        ids.add(cid)
        if not claim.get('statement') or claim.get('kind') not in ['reported', 'synthesis', 'limitation'] or not claim.get('refs'):
            raise ValueError('Review claim needs statement, kind and primary-note refs')
        if any(ref not in lookup for ref in claim['refs']):
            raise ValueError('Unknown source claim in ' + cid)
    if set(CITATION.findall(text)) != ids or not ids:
        raise ValueError('Undefined or absent citations')
    if re.search(r'\b(TODO|TBD|PLACEHOLDER)\b|待填写', text, re.I):
        raise ValueError('Unfinished review')
    parts = re.split(r'^##\s+(.+?)\s*$', text, flags=re.M)
    if len(parts) < 3:
        raise ValueError('Review needs level-two chapters')
    chapters = []
    for i in range(1, len(parts), 2):
        body = parts[i + 1]
        refs = list(dict.fromkeys(CITATION.findall(body)))
        if not refs:
            raise ValueError('Every chapter needs evidence-linked citations: ' + parts[i])
        chapters.append({'id': 'chapter-' + str(len(chapters) + 1), 'title': parts[i], 'body': body, 'refs': refs})
    return text, claims, chapters, lookup


def difference(previous, current, claims):
    def version(s):
        return s.get('version_hash') or digest(s['hash'] + digest(json.dumps(s['claims'], sort_keys=True, ensure_ascii=False)) + s['evidence_hash'])
    old = {s['key']: version(s) for s in (previous or {}).get('sources', [])}
    new = {s['key']: version(s) for s in current}
    old_claims = {c['id']: (c['statement'], c['refs'], c['kind']) for c in (previous or {}).get('claims', [])}
    return {'added_papers': sorted(new.keys() - old.keys()), 'removed_papers': sorted(old.keys() - new.keys()), 'changed_notes': sorted(k for k in new.keys() & old.keys() if new[k] != old[k]), 'changed_conclusions': [c['id'] for c in claims if c['id'] not in old_claims or old_claims[c['id']] != (c['statement'], c['refs'], c['kind'])], 'removed_conclusions': sorted(old_claims.keys() - {c['id'] for c in claims}), 'unresolved': [c['statement'] for c in claims if c['kind'] == 'limitation']}


def build(run, mcp=None):
    text, claims, chapters, lookup = validate(run)
    analysis_hash = analysis_digest(run, text, claims)
    renderer_hash = digest(json.dumps({str(p.relative_to(ASSETS)): digest(p.read_bytes()) for p in sorted(ASSETS.rglob('*')) if p.is_file()}, sort_keys=True))
    content_hash = digest(analysis_hash + renderer_hash)
    audit = read_json(run.path / 'audit.json')
    if audit.get('status') != 'passed' or audit.get('draft_hash') != digest(text) or audit.get('review_hash') != analysis_hash or not audit.get('reviewer') or not audit.get('checks'):
        raise ValueError('Independent audit must match the current review.md hash')
    if run.state.get('published_hash') == content_hash:
        verify_artifact(Path(run.state['version_path']))
        if mcp and run.state.get('status') == 'rendered':
            publish_zotero(run, mcp)
        prior = read_json(Path(run.state['version_path']) / 'manifest.json')
        desktop_copy = deliver_to_desktop(Path(run.state['version_path']).parent, Path(run.state['version_path']).name, prior.get('title', 'review'))
        result = {'version': run.state['version_path'], 'reused': True, 'item_key': run.state.get('item_key')}
        if desktop_copy:
            result['desktop_copy'] = str(desktop_copy)
        return result
    root = run.path.parents[1] / 'reviews' / digest(run.state['config']['title'])[:16]
    root.mkdir(parents=True, exist_ok=True)
    with lock(root / '.lock'):
        # Recover a completed rename even if the subsequent run checkpoint failed.
        for candidate in root.glob('*/manifest.json'):
            if candidate.parent.name.startswith('.'):
                continue
            prior = read_json(candidate)
            if prior.get('content_hash') == content_hash:
                verify_artifact(candidate.parent)
                run.state.update(status='rendered', version_path=str(candidate.parent), published_hash=content_hash)
                run.save()
                write_json(root / 'latest.json', {'version': candidate.parent.name, 'content_hash': content_hash})
                if mcp:
                    publish_zotero(run, mcp)
                prior_title = read_json(candidate).get('title', 'review')
                desktop_copy = deliver_to_desktop(root, candidate.parent.name, prior_title)
                result = {'version': str(candidate.parent), 'reused': True, 'item_key': run.state.get('item_key')}
                if desktop_copy:
                    result['desktop_copy'] = str(desktop_copy)
                return result
        latest = read_json(root / 'latest.json') if (root / 'latest.json').exists() else None
        previous = read_json(root / latest['version'] / 'manifest.json') if latest else None
        version = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
        stage = root / ('.building-' + version)
        stage.mkdir()
        shutil.copytree(run.path / 'sources', stage / 'sources')
        shutil.copytree(ASSETS / 'katex', stage / 'katex')
        for name in ['review.md', 'review-claims.json', 'matrix.json', 'matrix.csv', 'audit.json']:
            shutil.copyfile(run.path / name, stage / name)
        if 'scope' in run.state:
            write_json(stage / 'review-scope.json', run.state['scope'])
            for name in ['evidence-cards.json', 'synthesis-workbook.md']:
                shutil.copyfile(run.path / name, stage / name)
            disclosure = scope_disclosure(run.state['scope'])
            chapters.insert(0, {'id': 'scope', 'title': '本版证据范围', 'body': disclosure, 'refs': []})
            text = '# 本版证据范围\n\n' + disclosure + '\n\n' + text
        by_id = {c['id']: c for c in claims}
        for chapter in chapters:
            chapter['html'] = render_body(CITATION.sub(lambda m: '[' + m[1] + '](#evidence-' + m[1] + ')', chapter['body']))
            chapter['references'] = [by_id[cid] for cid in chapter['refs']]
        evidence_list = []
        for claim in claims:
            support = []
            for ref in claim['refs']:
                key, cid = ref.split(':')
                source = next(s for s in run.state['sources'] if s['key'] == key)
                packet = read_json(run.path / 'sources' / key / 'evidence.json')
                external = {e['id']: e for e in packet.get('external_sources', [])}
                locators = []
                for locator in lookup[ref]['evidence']:
                    entry = dict(locator)
                    ext = external.get(locator['source'], {})
                    attachment = ext.get('attachment_key') or (locator['source'] if re.fullmatch('[A-Z0-9]{8}', locator['source']) else None)
                    if attachment and locator.get('page'):
                        entry['locator_url'] = 'zotero://open-pdf/library/items/' + attachment + '?page=' + str(locator['page'])
                    elif ext.get('url', '').startswith(('https://', 'http://')):
                        entry['locator_url'] = ext['url']
                    locators.append(entry)
                support.append({'key': key, 'id': cid, 'title': source['title'], 'doi': source['doi'], 'note': source['note_path'], 'evidence': 'sources/' + key + '/evidence.json', 'claim': {**lookup[ref], 'evidence': locators}})
            evidence_list.append({**claim, 'support': support})
        exported = CITATION.sub(lambda m: '[' + m[1] + '](#' + m[1].lower() + ')', text) + '\n\n## 证据与参考文献\n'
        for item in evidence_list:
            exported += '\n### ' + item['id'] + '\n\n' + item['statement'] + '\n\n'
            for support in item['support']:
                positions = '; '.join(str(e['source']) + (': p.' + str(e['page']) if e.get('page') else '') for e in support['claim']['evidence'])
                exported += '- [' + support['title'] + '](' + ('https://doi.org/' + support['doi'] if support['doi'] else support['note']) + ') · [' + support['id'] + ' 精读](' + support['note'] + ') · [证据](' + support['evidence'] + ') · ' + positions + '\n'
        (stage / 'review.md').write_text(exported, encoding='utf-8')
        changes = difference(previous, run.state['sources'], claims)
        manifest = {'schema': 1, 'version': version, 'created_at': now(), 'title': run.state['config']['title'], 'library_id': run.state['config']['library'], 'content_hash': content_hash, 'analysis_hash': analysis_hash, 'renderer_hash': renderer_hash, 'sources': run.state['sources'], 'claims': claims, 'previous': latest['version'] if latest else None, 'changes': changes}
        write_json(stage / 'evidence-list.json', evidence_list)
        write_json(stage / 'changes.json', changes)
        env = Environment(loader=FileSystemLoader(str(ASSETS)), autoescape=select_autoescape(['html']))
        page = env.get_template('review.html').render(title=manifest['title'], timestamp=manifest['created_at'], version=version, chapters=chapters, evidence=evidence_list, papers=run.state['sources'], changes=changes)
        (stage / 'review.html').write_text(page, encoding='utf-8')
        manifest['files'] = {p.relative_to(stage).as_posix(): digest(p.read_bytes()) for p in stage.rglob('*') if p.is_file()}
        write_json(stage / 'manifest.json', manifest)
        dest = root / version
        stage.rename(dest)
        write_json(root / 'latest.json', {'version': version, 'content_hash': content_hash})
        run.state.update(status='rendered', version_path=str(dest), published_hash=content_hash)
        run.save()
    if mcp:
        publish_zotero(run, mcp)
    desktop_copy = deliver_to_desktop(root, version, manifest['title'])
    result = {'version': str(dest), 'reused': False, 'item_key': run.state.get('item_key'), 'changes': changes}
    if desktop_copy:
        result['desktop_copy'] = str(desktop_copy)
    return result


def review_destination():
    """Where finished review versions are mirrored. Desktop by default."""
    import os
    return Path(os.environ.get("ZOTERO_SKILLS_REVIEW_DEST", str(Path.home() / "Desktop")))


def deliver_to_desktop(root, version, title):
    """Copy the immutable version directory (review.html + evidence pack) to the
    user-facing destination. A pure mirror: the canonical version stays under reviews/."""
    dest_root = review_destination().resolve()
    if not dest_root.is_dir():
        return None
    safe_title = re.sub(r'[\\/:*?"<>|]+', '', title).strip() or 'review'
    target = dest_root / (safe_title + '-' + version)
    try:
        if not target.resolve().is_relative_to(dest_root):
            raise ValueError('Review mirror target is outside its destination')
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(root / version, target)
        offline_zip = root / (version + '-offline.zip')
        if offline_zip.is_file():
            shutil.copyfile(offline_zip, dest_root / (safe_title + '-' + version + '-offline.zip'))
    except OSError:
        return None
    return target


def audit_hash(run):
    text, claims, _, _ = validate(run)
    return analysis_digest(run, text, claims)


def analysis_digest(run, text, claims):
    payload = [text, claims, run.state['sources']]
    if 'scope' in run.state:
        payload.append(run.state['scope'])
    return digest(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def verify_artifact(directory):
    manifest = read_json(directory / 'manifest.json')
    for name, expected in manifest['files'].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError('Immutable review artifact changed: ' + name)
    return manifest


def publish_zotero(run, mcp):
    from .notes import render_markdown
    directory = Path(run.state['version_path'])
    manifest = verify_artifact(directory)
    library = run.state['config']['library']
    if library != manifest['library_id']:
        raise ValueError('Review library changed')
    note_text = (directory / 'review.md').read_text(encoding='utf-8')
    note_text = re.sub(r'\]\(sources/([A-Z0-9]{8})/(?:note\.md|evidence\.json)\)', r'](zotero://select/library/items/\1)', note_text)
    note_text = re.sub(r'\[(R\d+)\]\(#r\d+\)', r'[\1]', note_text)
    collection = mcp.ensure_collection('Zotero Skills - 版本化综述', library)
    key = mcp.js("""
const marker='zotero-skills:review:'+P.hash;const s=new Zotero.Search();s.libraryID=P.library;s.addCondition('tag','is',marker);const found=await Zotero.Items.getAsync(await s.search());let x=found.find(x=>!x.deleted&&x.isRegularItem());
if(!x){x=new Zotero.Item('report');x.libraryID=P.library;x.setField('title',P.title);x.setField('date',P.date);x.setField('extra','Offline review: '+P.path);x.addTag(marker);x.addToCollection((await Zotero.Collections.getByLibraryAndKeyAsync(P.library,P.collection)).id);await x.saveTx();}
const notes=await Zotero.Items.getAsync(x.getNotes());if(!notes.some(n=>n.hasTag(marker)&&n.getNote().trim()===P.html.trim())){const n=new Zotero.Item('note');n.libraryID=P.library;n.parentItemID=x.id;n.setNote(P.html);n.addTag(marker);await n.saveTx();}return x.key;
""", library=library, hash=manifest['content_hash'], title=manifest['title'] + ' · ' + manifest['version'], date=manifest['created_at'][:10], path=str(directory / 'review.html'), collection=collection, html=render_markdown(note_text))
    md = mcp.attach(key, directory / 'review.md', '综述 Markdown', library)
    # HTML depends on fonts/scripts and source files. Store a complete offline ZIP.
    bundle = Path(shutil.make_archive(str(directory.parent / (directory.name + '-offline')), 'zip', directory))
    archive = mcp.attach(key, bundle, '综述离线 HTML 与完整证据包', library)
    snapshot = mcp.snapshot(key, library)
    if not snapshot['notes'] or not {md['key'], archive['key']} <= {a['key'] for a in snapshot['attachments']}:
        raise RuntimeError('Review publication readback failed')
    run.state.update(status='complete', item_key=key)
    run.save()
    write_json(directory.parent / (directory.name + '-publication.json'), {'item_key': key, 'library': library, 'markdown_key': md['key'], 'archive_key': archive['key'], 'at': now()})


def register(sub):
    p = sub.add_parser('review', help='Prepare evidence matrix or publish an audited synthesis')
    p.add_argument('--title', default='领域文献综述')
    p.add_argument('--source-run', action='append', type=Path, default=[])
    p.add_argument('--collection')
    p.add_argument('--topic')
    p.add_argument('--library', type=int, default=1)
    p.add_argument('--publish', action='store_true')
    p.add_argument('--run', type=Path)


def execute(args):
    if args.publish:
        if not args.run:
            raise ValueError('--publish requires --run')
        with lock(write_lock_path()):
            run = Run(args.run)
            return build(run, MCP(args.url))
    return prepare(args.output, args.title, args.source_run, args.collection, args.topic, args.library, MCP(args.url) if args.collection or args.topic else None)


def resume(run, args):
    if not (run.path / 'audit.json').exists():
        return {'run': str(run.path), 'status': 'awaiting_synthesis_and_audit'}
    with lock(write_lock_path()):
        return build(run, MCP(args.url))
