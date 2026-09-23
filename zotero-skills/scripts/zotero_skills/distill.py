"""Exhaustive library selection and source-sensitive reuse of reviewed notes."""
import json
import shutil
from pathlib import Path

from .core import MCP, Network, Run, digest, lock, read_json
from .library import enumerate_items
from .notes import render_markdown, split_frontmatter, validate_note
from .search import collect_evidence


def reusable(run, paper, mcp):
    library = run.state['config']['library']
    root = run.path.parents[1] / 'notes' / str(library) / paper['item_key']
    archives = sorted(root.glob('*/publication.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not archives:
        return False
    snap = mcp.snapshot(paper['item_key'], library)
    for publication in archives:
        directory = publication.parent
        e = read_json(directory / 'evidence.json')
        manifest = read_json(publication)
        note = (directory / 'note.md').read_text(encoding='utf-8')
        claims = read_json(directory / 'claims.json')
        try:
            _, body = validate_note(note, claims, e)
        except ValueError:
            continue
        if not any(n['key'] == manifest['note_key'] and n['html'].strip() == render_markdown(body).strip() for n in snap['notes']):
            continue  # Human edits stay intact and are read as context in a new run.
        if any(e['metadata'].get(f) != snap['item'].get(f) for f in ['title', 'abstractNote', 'DOI', 'creators', 'date']):
            continue
        old = sorted(s['sha256'] for s in e['sources'] if s['type'] == 'pdf')
        current = sorted(digest(Path(a['path']).read_bytes()) for a in snap['attachments'] if a.get('contentType') == 'application/pdf' and a.get('path') and Path(a['path']).is_file())
        human = lambda notes: {n['key']: n['html'] for n in notes if not any(t['tag'].startswith('zotero-skills:') for t in n.get('tags', []))}
        annotations = [a for att in snap['attachments'] for a in att.get('annotations', [])]
        if old != current or human(e.get('user_notes', [])) != human(snap['notes']) or annotations != e.get('annotations', []):
            continue
        target = run.paper_dir(paper)
        for name in ['note.md', 'claims.json', 'evidence.json', 'publication.json']:
            shutil.copyfile(directory / name, target / name)
        (target / 'fulltext.txt').write_text('\n\n'.join(f"[{p['source']} p.{p['page']}]\n{p['text']}" for p in e.get('pages', [])) or e.get('abstract', ''), encoding='utf-8')
        paper.update(status='published', reused_analysis=True, note_key=manifest['note_key'], note_hash=manifest['content_hash'], evidence_level=e['level'], markdown_attachment_key=manifest['markdown_attachment_key'])
        run.save()
        return True
    return False


def process(run, mcp, net, retry=False, refresh=False):
    for paper in run.state['papers']:
        if paper['status'] in ['published', 'awaiting_analysis'] and not refresh:
            continue
        if paper['status'] == 'error' and not retry:
            continue
        try:
            if not refresh and reusable(run, paper, mcp):
                continue
            collect_evidence(run, paper, mcp, net)
        except Exception as exc:
            paper.update(status='error', error=type(exc).__name__ + ': ' + str(exc))
            run.save()
    statuses = [p['status'] for p in run.state['papers']]
    run.state['status'] = 'complete' if all(s == 'published' for s in statuses) else 'partial_failure' if 'error' in statuses else 'awaiting_analysis'
    run.save()
    return {'run': str(run.path), 'status': run.state['status'], 'total': len(statuses), 'published': statuses.count('published'), 'awaiting_analysis': statuses.count('awaiting_analysis'), 'errors': statuses.count('error'), 'next': 'Host agent reads every evidence bundle, writes note.md + claims.json and publish-note; no analysis API needed.'}


def register(sub):
    p = sub.add_parser('distill', help='Read all papers in a collection subtree or matching a topic')
    scope = p.add_mutually_exclusive_group(required=True)
    scope.add_argument('--collection')
    scope.add_argument('--topic', help='Case-insensitive title/abstract/tag phrase; use a curated collection for semantic scope')
    p.add_argument('--library', type=int, default=1)
    p.add_argument('--page-size', type=int, default=100)
    p.add_argument('--years', help='Inclusive START:END')
    p.add_argument('--refresh', action='store_true', help='Re-read sources instead of reusing unchanged published notes')


def execute(args):
    mcp = MCP(args.url)
    rows = enumerate_items(mcp, args.library, args.collection, args.topic, args.page_size)
    if args.years:
        low, high = map(int, args.years.split(':'))
        rows = [r for r in rows if str(r.get('date', ''))[:4].isdigit() and low <= int(r['date'][:4]) <= high]
    run = Run.create(args.output, 'distill', {'library': args.library, 'collection': args.collection, 'topic': args.topic, 'years': args.years, 'page_size': args.page_size})
    run.state['papers'] = [{'id': digest(str(args.library) + ':' + r['key'])[:20], 'item_key': r['key'], 'title': r.get('title', ''), 'doi': r.get('DOI'), 'abstract': r.get('abstractNote', ''), 'url': r.get('url'), 'status': 'selected', 'pdf_urls': []} for r in rows]
    run.save()  # Freeze all identities before any per-item work.
    with lock(run.path / '.lock'), lock(args.output / '.zotero-write.lock'):
        return process(run, mcp, Network(args.output / 'cache'), refresh=args.refresh)


def resume(run, args):
    with lock(args.output / '.zotero-write.lock'):
        return process(run, MCP(args.url), Network(args.output / 'cache'), retry=args.retry_errors)
