"""Conservative identity matching and recoverable, attachment-preserving native merge."""
import difflib
import json
import re
from pathlib import Path

from .core import write_lock_path
from .core import MCP, Run, digest, lock, now, read_json, write_json
from .library import enumerate_items


def normalized(value):
    return re.sub(r'[^\w]', '', str(value or '').casefold())


def identifier(item):
    doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', item.get('DOI', '').strip(), flags=re.I).lower()
    if doi:
        return 'doi:' + doi
    arxiv = re.search(r'arxiv\.org/(?:abs|pdf)/((?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7})(?:v\d+)?)', item.get('url', ''), re.I)
    return 'arxiv:' + arxiv[1] if arxiv else None  # Versions deliberately distinct.


def compatible(items):
    first = items[0]
    for item in items[1:]:
        if item['itemType'] != first['itemType']:
            return False
        a, b = normalized(first.get('title')), normalized(item.get('title'))
        if a and b and difflib.SequenceMatcher(None, a, b).ratio() < .94:
            return False
        a, b = str(first.get('date', ''))[:4], str(item.get('date', ''))[:4]
        if a and b and a != b:
            return False
        a, b = first.get('creators', []), item.get('creators', [])
        if a and b and normalized(a[0].get('lastName', a[0].get('name'))) != normalized(b[0].get('lastName', b[0].get('name'))):
            return False
    return True


def groups(items):
    by_id, automatic, review = {}, [], []
    for x in items:
        ident = identifier(x)
        if ident:
            by_id.setdefault(ident, []).append(x)
    assigned = set()
    for ident, rows in by_id.items():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda x: (x.get('dateAdded', ''), x['key']))
        entry = {'identity': ident, 'keys': [x['key'] for x in rows]}
        (automatic if compatible(rows) else review).append(entry)
        assigned.update(entry['keys'])
    # Similar titles are review-only, including records with different identifiers.
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if a['key'] in assigned and b['key'] in assigned and identifier(a) == identifier(b):
                continue
            ta, tb = normalized(a.get('title')), normalized(b.get('title'))
            if min(len(ta), len(tb)) >= 15 and difflib.SequenceMatcher(None, ta, tb).ratio() >= .9:
                review.append({'keys': [a['key'], b['key']], 'reason': 'Title similarity is not proof of identity'})
    return automatic, review


TREE = """
async function snapshot(k){const x=await Zotero.Items.getByLibraryAndKeyAsync(P.library,k);if(!x)throw new Error('Missing '+k);await x.reload(null,true);
const data={key:x.key,id:x.id,parent:x.parentItemKey||null,deleted:!!x.deleted,json:x.toJSON(),uri:Zotero.URI.getItemURI(x)};
if(x.isNote()||x.isAttachment())data.note=x.getNote();
if(x.isAttachment()){data.path=await x.getFilePathAsync();data.imported=x.isImportedAttachment();}
let ids=x.isRegularItem()?[...x.getNotes(true),...x.getAttachments(true)] : (x.isNote()?await Zotero.DB.columnQueryAsync('SELECT itemID FROM itemAttachments WHERE parentItemID=?',[x.id]):(x.isAttachment()&&(x.isPDFAttachment()||x.isEPUBAttachment())?x.getAnnotations(true).map(a=>a.id):[]));
data.children=await Promise.all(ids.map(async id=>snapshot((await Zotero.Items.getAsync(id)).key)));return data;}
return await Promise.all(P.keys.map(snapshot));
"""


def tree(mcp, keys, library):
    rows = mcp.read_large(TREE, keys=keys, library=library)
    def files(node):
        path = Path(node['path']) if node.get('path') else None
        node['files'] = {}
        if path and path.is_file():
            paths = list(path.parent.rglob('*')) if node.get('imported') else [path]
            for p in paths:
                if p.is_file() and not p.name.startswith('.zotero'):
                    node['files'][str(p)] = digest(p.read_bytes())
        for c in node['children']:
            files(c)
    for row in rows:
        files(row)
    return rows


def flat(rows):
    result = {}
    def walk(node):
        result[node['key']] = node
        for child in node['children']:
            walk(child)
    for row in rows:
        walk(row)
    return result


def verify(before, after):
    errors = []
    old, new = flat(before), flat(after)
    master = before[0]['key']
    losers = {x['key'] for x in before[1:]}
    for key, node in old.items():
        current = new.get(key)
        if not current:
            errors.append('Missing key ' + key)
            continue
        if current['deleted'] != (True if key in losers else node['deleted']):
            errors.append('Deleted state changed ' + key)
        if key not in losers | {master}:
            expected_parent = master if node['parent'] in losers else node['parent']
            if current['parent'] != expected_parent or node['files'] != current['files']:
                errors.append('Parent or file hash mismatch ' + key)
            if node['json']['itemType'] == 'annotation':
                for field, value in node['json'].items():
                    if field.startswith('annotation') and current['json'].get(field) != value:
                        errors.append('Annotation changed ' + key + ':' + field)
            if node.get('note'):
                expected = node['note']
                if node['json']['itemType'] == 'note' and node['parent'] in losers:
                    loser = node['parent']
                    expected = expected.replace('%2Fitems%2F' + loser, '%2Fitems%2F' + master).replace('data-attachment-key="' + loser + '"', 'data-attachment-key="' + master + '"', 1)
                if current.get('note') not in [node['note'], expected]:
                    errors.append('Note changed unexpectedly ' + key)
    collections = {c for x in before for c in x['json'].get('collections', [])}
    tags = {t['tag'] for x in before for t in x['json'].get('tags', [])}
    if not collections <= set(new[master]['json'].get('collections', [])):
        errors.append('Collection union incomplete')
    if not tags <= {t['tag'] for t in new[master]['json'].get('tags', [])}:
        errors.append('Tag union incomplete')
    relations = new[master]['json'].get('relations', {})
    for source in before:
        for pred, values in source['json'].get('relations', {}).items():
            values = values if isinstance(values, list) else [values]
            got = relations.get(pred, [])
            got = got if isinstance(got, list) else [got]
            internal = {x['uri'] for x in before} if pred != 'dc:replaces' else {before[0]['uri']}
            if not set(values) - internal <= set(got):
                errors.append('Relation lost ' + pred)
    got = relations.get('dc:replaces', [])
    if isinstance(got, str):
        got = [got]
    if not {x['uri'] for x in before[1:]} <= set(got):
        errors.append('Old reference mapping missing')
    if errors:
        raise RuntimeError('; '.join(errors))
    return {'passed': True, 'preserved_child_keys': len(old) - len(before), 'collections': sorted(collections), 'checked_at': now()}


def committed_state(mcp, manifest):
    # SQL is authoritative after an interrupted transaction, unlike cached Items.
    return mcp.js("""
if(Zotero.DB.inTransaction())throw new Error('Transaction still running; retry later');
const rows=await Zotero.DB.queryAsync('SELECT i.key, d.itemID IS NOT NULL AS deleted FROM items i LEFT JOIN deletedItems d USING(itemID) WHERE i.libraryID=? AND i.key IN ('+P.keys.map(()=>'?').join(',')+')',[P.library,...P.keys]);return rows.map(r=>({key:r.key,deleted:r.deleted}));
""", library=manifest['library'], keys=manifest['keys'])


def merge_group(mcp, directory, keys, library=1, inject=None, recover=False):
    if len(keys) < 2 or len(set(keys)) != len(keys):
        raise ValueError('Merge needs at least two distinct keys')
    directory = Path(directory)
    path = directory / 'merge.json'
    if recover and not path.exists():
        raise ValueError('No existing preparation manifest to restore')
    if path.exists():
        manifest = read_json(path)
        if keys != manifest['keys'] or library != manifest['library']:
            raise ValueError('Manifest belongs to a different group/library')
        if manifest['state'] == 'complete':
            return manifest['verification']
        actual = committed_state(mcp, manifest)
        states = {x['key']: bool(x['deleted']) for x in actual}
        if states.get(keys[0]) is False and all(states.get(k) for k in keys[1:]):
            # A native failure may leave a stale relation cache. Require restart.
            if manifest['state'] == 'native_uncertain' and mcp.js('return Zotero.initializationTime?.toString()||Services.appinfo.processID;') == manifest.get('process'):
                raise RuntimeError('Restart Zotero before recovering an uncertain native merge')
            return finish_merge(mcp, path, manifest, inject)
        if any(states.get(k) is not False for k in keys):
            raise RuntimeError('Mixed/missing committed state: retain manifest for manual recovery')
        if manifest['state'] == 'native_uncertain':
            if mcp.js('return Zotero.initializationTime?.toString()||Services.appinfo.processID;') == manifest.get('process'):
                raise RuntimeError('Restart Zotero before recovering a rolled-back native merge')
        if recover:
            moves = [{'key': c['key'], 'parent': x['key']} for x in manifest['before'][1:] for c in x['children']]
            mcp.js("""
await Zotero.DB.executeTransaction(async()=>{for(const move of P.moves){const x=await Zotero.Items.getByLibraryAndKeyAsync(P.library,move.key);if(!x||![P.master,move.parent].includes(x.parentItemKey))throw new Error('Changed attachment; cannot restore');x.parentItemKey=move.parent;await x.save();}});return true;
""", library=library, master=keys[0], moves=moves)
            manifest['state'] = 'restored'
            write_json(path, manifest)
            return {'restored': True}
    else:
        before = tree(mcp, keys, library)
        if any(x['deleted'] or x['json']['itemType'] in ['attachment', 'note'] for x in before) or not compatible([x['json'] for x in before]):
            raise ValueError('Group is not a compatible set of live parent items')
        if len({identifier(x['json']) for x in before}) != 1 or not identifier(before[0]['json']):
            raise ValueError('Automatic merge requires an identical stable identifier')
        conflicts = {}
        for field in set().union(*(x['json'] for x in before)) - {'key', 'version', 'dateAdded', 'dateModified', 'collections', 'tags', 'relations'}:
            vals = {x['key']: x['json'][field] for x in before if x['json'].get(field)}
            if len({json.dumps(v, sort_keys=True) for v in vals.values()}) > 1:
                conflicts[field] = vals
        manifest = {'schema': 1, 'library': library, 'keys': keys, 'state': 'preflight', 'created_at': now(), 'before': before, 'conflicts': conflicts, 'process': mcp.js('return Zotero.initializationTime?.toString()||Services.appinfo.processID;')}
        write_json(path, manifest)
    # Idempotent preparation; the exact recorded attachment set prevents new files
    # added by a user during the job from being folded by native merge.
    refreshed = tree(mcp, keys, library)  # Refresh caches after preparation rollback.
    for original, current_parent in zip(manifest['before'], refreshed):
        for field in set(original['json']) | set(current_parent['json']):
            if field not in {'version', 'dateModified'} and original['json'].get(field) != current_parent['json'].get(field):
                raise RuntimeError('Parent metadata changed since preflight: ' + original['key'] + ':' + field)
    expected = {x['key']: [c['key'] for c in x['children']] for x in manifest['before'][1:]}
    mcp.js("""
const master=await Zotero.Items.getByLibraryAndKeyAsync(P.library,P.keys[0]);
await Zotero.DB.executeTransaction(async()=>{for(const key of P.keys.slice(1)){const other=await Zotero.Items.getByLibraryAndKeyAsync(P.library,key);if(!other||other.deleted||master.deleted)throw new Error('Parent changed');for(const id of [...other.getAttachments(true),...other.getNotes(true)]){const a=await Zotero.Items.getAsync(id);if(!P.expected[key].includes(a.key))throw new Error('Unexpected new child');a.parentItemID=master.id;await a.save();}}
if(P.inject==='prepare')throw new Error('Injected preparation rollback');});return true;
""", library=library, keys=keys, expected=expected, inject=inject)
    manifest['state'] = 'prepared'
    write_json(path, manifest)
    if inject == 'after_prepare':
        raise RuntimeError('Injected stop after committed preparation')
    prepared = tree(mcp, keys, library)
    old, current = flat(manifest['before']), flat(prepared)
    for key, node in old.items():
        if key not in current or node['files'] != current[key]['files']:
            raise RuntimeError('Child or file changed before native merge: ' + key)
        if node['parent'] in keys and current[key]['parent'] != keys[0]:
            raise RuntimeError('Attachment moved outside master: ' + key)
    # Persist BEFORE dispatch: timeout can mean committed merge.
    manifest['state'] = 'native_uncertain'
    manifest['process'] = mcp.js('return Zotero.initializationTime?.toString()||Services.appinfo.processID;')
    write_json(path, manifest)
    mcp.js("""
const {mergeItems}=ChromeUtils.importESModule('chrome://zotero/content/mergeItems.mjs');
const items=await Promise.all(P.keys.map(k=>Zotero.Items.getByLibraryAndKeyAsync(P.library,k)));
if(items.some(x=>!x||x.deleted)||items.slice(1).some(x=>x.getAttachments(true).length||x.getNotes(true).length)||Zotero.DB.inTransaction())throw new Error('Native merge precondition changed');
for(let i=0;i<items.length;i++){const actual=items[i].toJSON();for(const field of new Set([...Object.keys(actual),...Object.keys(P.parents[i])]))if(!['version','dateModified'].includes(field)&&JSON.stringify(actual[field])!==JSON.stringify(P.parents[i][field]))throw new Error('Parent metadata changed before native merge');}
const pending=mergeItems(items[0],items.slice(1));await pending;return true;
""", library=library, keys=keys, parents=[x['json'] for x in prepared])
    manifest['state'] = 'native_committed'
    write_json(path, manifest)
    if inject == 'after_native':
        raise RuntimeError('Injected stop after native commit')
    return finish_merge(mcp, path, manifest, inject)


def finish_merge(mcp, path, manifest, inject=None):
    keys, library = manifest['keys'], manifest['library']
    committed_state(mcp, manifest)  # Wait/reject while an uncertain RPC still owns DB.
    tree(mcp, keys, library)  # Reload fields after a possible finalization rollback.
    # Fill only empty valid bibliographic fields, retain conflicting originals in
    # the durable manifest and a human-readable child note.
    from .notes import render_markdown
    audit = '# 无损合并记录\n\n' + now() + '\n\n旧条目映射：' + ', '.join(keys[1:]) + ' → ' + keys[0] + '\n\n字段冲突（保留最早记录值）：\n\n```json\n' + json.dumps(manifest['conflicts'], ensure_ascii=False, indent=2) + '\n```'
    mcp.js("""
const x=await Zotero.Items.getByLibraryAndKeyAsync(P.library,P.keys[0]);
await Zotero.DB.executeTransaction(async()=>{for(const source of P.sources){for(const [field,value] of Object.entries(source)){const fid=Zotero.ItemFields.getID(field);if(fid&&Zotero.ItemFields.isValidForType(fid,x.itemTypeID)&&!x.getField(field)&&value)x.setField(field,value);}if(!x.getCreators().length&&source.creators?.length)x.setCreators(source.creators);}await x.save();
if(P.inject==='finish')throw new Error('Injected finalization rollback');const tag='zotero-skills:merge:'+P.keys.join('-');const notes=await Zotero.Items.getAsync(x.getNotes());if(!notes.some(n=>n.hasTag(tag))){const n=new Zotero.Item('note');n.libraryID=P.library;n.parentItemID=x.id;n.setNote(P.html);n.addTag(tag);await n.save();}});return true;
""", library=library, keys=keys, sources=[x['json'] for x in manifest['before'][1:]], html=render_markdown(audit), inject=inject)
    after = tree(mcp, keys, library)
    if not any(any(t['tag'] == 'zotero-skills:merge:' + '-'.join(keys) for t in n['json'].get('tags', [])) for n in after[0]['children']):
        raise RuntimeError('Merge audit note missing')
    for source in manifest['before'][1:]:
        for field, value in source['json'].items():
            if value and field in after[0]['json'] and not manifest['before'][0]['json'].get(field) and not after[0]['json'].get(field):
                raise RuntimeError('Empty field was not filled: ' + field)
    manifest['verification'] = verify(manifest['before'], after)
    manifest.update(state='complete', after=after)
    write_json(path, manifest)
    return manifest['verification']


def register(sub):
    p = sub.add_parser('dedup', help='Plan safe merges; --apply executes exact-identity groups')
    p.add_argument('--library', type=int, default=1)
    p.add_argument('--collection')
    p.add_argument('--apply', action='store_true')


def execute(args):
    mcp = MCP(args.url)
    rows = enumerate_items(mcp, args.library, args.collection)
    automatic, review = groups(rows)
    run = Run.create(args.output, 'dedup', {'library': args.library, 'collection': args.collection, 'apply': args.apply})
    run.state.update(groups=automatic, review=review, status='planned')
    run.save()
    return resume(run, args) if args.apply else {'run': str(run.path), 'automatic_groups': len(automatic), 'needs_review': len(review), 'status': 'planned; resume to apply'}


def resume(run, args):
    with lock(write_lock_path()):
        mcp = MCP(args.url)
        for group in run.state['groups']:
            if group.get('status') == 'complete':
                continue
            directory = run.path / 'merges' / digest(group['keys'])[:16]
            restoring = getattr(args, 'restore', False)
            if restoring and not (directory / 'merge.json').exists():
                continue
            result = merge_group(mcp, directory, group['keys'], run.state['config']['library'], recover=restoring)
            group.update(status='restored' if result.get('restored') else 'complete', verification=result)
            run.save()
    run.state['status'] = 'restored' if getattr(args, 'restore', False) else 'complete'
    run.save()
    return {'run': str(run.path), 'merged_groups': len(run.state['groups']), 'needs_review': len(run.state['review'])}
