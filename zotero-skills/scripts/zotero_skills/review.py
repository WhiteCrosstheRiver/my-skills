"""Host-written synthesis, grounded citations, offline rendering and immutable versions."""
import csv
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


def section(body, heading):
    match = re.search(r'^##\s+' + re.escape(heading) + r'\s*\n(.*?)(?=^##\s|\Z)', body, re.M | re.S)
    return match[1].strip() if match else ''


def prepare(output, title, source_runs=(), collection=None, topic=None, library=1, mcp=None):
    publications = {}
    for source in source_runs:
        run = Run(source)
        for paper in run.state['papers']:
            path = run.paper_dir(paper) / 'publication.json'
            if paper['status'] == 'published' and path.is_file():
                pub = read_json(path)
                key = str(pub['library_id']) + ':' + pub['item_key']
                previous = publications.get(key)
                if previous is None or pub['published_at'] > read_json(previous)['published_at']:
                    publications[key] = path
    if collection or topic:
        for item in enumerate_items(mcp or MCP(), library, collection, topic):
            files = list((Path(output) / 'notes' / str(library) / item['key']).glob('*/publication.json'))
            if files:
                path = max(files, key=lambda p: read_json(p)['published_at'])
                publications[str(library) + ':' + item['key']] = path
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
        _, body = validate_note(note, claims, evidence)
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
        matrix.append({'key': key, 'title': entry['title'], 'question': section(body, '背景与研究问题'), 'method': section(body, '关键方法与过程'), 'results': section(body, '结果与对照'), 'strength': evidence['level'], 'conflicts': section(body, '局限与矛盾'), 'claim_ids': [c['id'] for c in claims]})
    run.state.update(sources=sources, status='awaiting_synthesis')
    run.save()
    write_json(run.path / 'matrix.json', matrix)
    with (run.path / 'matrix.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(matrix[0]))
        writer.writeheader(); writer.writerows(matrix)
    return {'run': str(run.path), 'papers': len(sources), 'status': 'awaiting_synthesis', 'next': 'Read matrix.json and source notes. Write review.md using [R1] citations and review-claims.json [{id,statement,kind,refs:[ITEMKEY:C1]}]. Independently audit before review --publish --run PATH.'}


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
    analysis_hash = digest(json.dumps([text, claims, run.state['sources']], ensure_ascii=False, sort_keys=True))
    renderer_hash = digest(json.dumps({str(p.relative_to(ASSETS)): digest(p.read_bytes()) for p in sorted(ASSETS.rglob('*')) if p.is_file()}, sort_keys=True))
    content_hash = digest(analysis_hash + renderer_hash)
    audit = read_json(run.path / 'audit.json')
    if audit.get('status') != 'passed' or audit.get('draft_hash') != digest(text) or audit.get('review_hash') != analysis_hash or not audit.get('reviewer') or not audit.get('checks'):
        raise ValueError('Independent audit must match the current review.md hash')
    if run.state.get('published_hash') == content_hash:
        verify_artifact(Path(run.state['version_path']))
        if mcp and run.state.get('status') == 'rendered':
            publish_zotero(run, mcp)
        return {'version': run.state['version_path'], 'reused': True, 'item_key': run.state.get('item_key')}
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
                return {'version': str(candidate.parent), 'reused': True, 'item_key': run.state.get('item_key')}
        latest = read_json(root / 'latest.json') if (root / 'latest.json').exists() else None
        previous = read_json(root / latest['version'] / 'manifest.json') if latest else None
        version = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
        stage = root / ('.building-' + version)
        stage.mkdir()
        shutil.copytree(run.path / 'sources', stage / 'sources')
        shutil.copytree(ASSETS / 'katex', stage / 'katex')
        for name in ['review.md', 'review-claims.json', 'matrix.json', 'matrix.csv', 'audit.json']:
            shutil.copyfile(run.path / name, stage / name)
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
    return {'version': str(dest), 'reused': False, 'item_key': run.state.get('item_key'), 'changes': changes}


def audit_hash(run):
    text, claims, _, _ = validate(run)
    return digest(json.dumps([text, claims, run.state['sources']], ensure_ascii=False, sort_keys=True))


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
