import os
import uuid

import fitz
import pytest

from zotero_skills.core import MCP, default_output, read_json
from zotero_skills.dedup import groups, merge_group, tree


def test_matching_requires_identifier_and_consistent_metadata():
    a = dict(key='A', itemType='journalArticle', DOI='https://doi.org/10.1/x', title='A scientific title long enough', date='2020', dateAdded='2020')
    b = dict(a, key='B', DOI='10.1/x')
    assert len(groups([a, b])[0]) == 1
    assert not groups([a, dict(b, date='2021')])[0]
    assert not groups([a, dict(b, DOI='10.1/y')])[0]
    assert not groups([dict(a, DOI=''), dict(b, DOI='')])[0]


def fixture(mcp, directory):
    directory.mkdir(parents=True)
    doc = fitz.open(); page = doc.new_page(); page.insert_text((72, 72), 'Zotero Skills synthetic merge test')
    doc.save(directory / 'same.pdf'); doc.close()
    (directory / 'one.html').write_text('<h1>同名快照甲，内容必须保留</h1>', encoding='utf-8')
    (directory / 'two.html').write_text('<h1>同名快照乙，完全不同内容</h1>', encoding='utf-8')
    return mcp.js("""
const root=new Zotero.Collection();root.libraryID=1;root.name='Zotero Skills Tests - Merge '+P.token;await root.saveTx();
const parents=[];
for(let i=0;i<2;i++){
const c=new Zotero.Collection();c.libraryID=1;c.name=i?'D2':'D1';c.parentID=root.id;await c.saveTx();
const x=new Zotero.Item('journalArticle');x.libraryID=1;x.setField('title','[TEST] Lossless merge '+P.token);x.setField('DOI','10.99999/zotero-skills-test-'+P.token);x.setField('date','2026');x.setField('dateAdded',i?'2026-02-01 00:00:00':'2026-01-01 00:00:00');x.setField('extra',i?'冲突字段乙':'冲突字段甲');if(i)x.setField('abstractNote','合并后补齐的摘要');x.addToCollection(c.id);x.addTag('test-tag-'+i);await x.saveTx();parents.push(x);
const n=new Zotero.Item('note');n.libraryID=1;n.parentItemID=x.id;n.setNote('<p>人工笔记 '+i+'：禁止删除。字面 key '+x.key+'</p><span data-citation="%2Fitems%2F'+x.key+'">编码引用</span>');await n.saveTx();
const a=await Zotero.Attachments.importFromFile({file:P.pdf,parentItemID:x.id,title:'Same PDF'});
const ann=new Zotero.Item('annotation');ann.libraryID=1;ann.parentItemID=a.id;ann.annotationType='highlight';ann.annotationText='Annotation '+i;ann.annotationComment='不同批注 '+i;ann.annotationColor='#ffd400';ann.annotationPageLabel='1';ann.annotationSortIndex='00000|000001|00000';ann.annotationPosition=JSON.stringify({pageIndex:0,rects:[[72,72,180,90]]});await ann.saveTx();
await Zotero.Attachments.importFromFile({file:P.html[i],parentItemID:x.id,title:'Same snapshot'});
}
parents[1].addRelation('dc:relation','https://example.org/synthetic-related');await parents[1].saveTx();
const third=new Zotero.Item('journalArticle');third.libraryID=1;third.setField('title',parents[0].getField('title'));third.setField('DOI',parents[0].getField('DOI'));third.setField('date','2026');third.addRelation('dc:relation',Zotero.URI.getItemURI(parents[1]));await third.saveTx();parents.push(third);
return {keys:parents.map(x=>x.key),collection:root.key};
""", token=directory.name, pdf=str(directory / 'same.pdf'), html=[str(directory / 'one.html'), str(directory / 'two.html')])


@pytest.mark.skipif(os.environ.get('ZOTERO_SKILLS_LIVE') != '1', reason='Opt-in synthetic library writes')
def test_live_lossless_merge_and_recovery():
    mcp = MCP()
    directory = default_output() / 'validation' / ('merge-' + uuid.uuid4().hex[:10])
    f = fixture(mcp, directory / 'fixture')
    before = tree(mcp, f['keys'], 1)
    with pytest.raises(RuntimeError, match='Injected preparation rollback'):
        merge_group(mcp, directory / 'operation', f['keys'], inject='prepare')
    rolled_back = tree(mcp, f['keys'], 1)
    assert [[c['key'] for c in x['children']] for x in rolled_back] == [[c['key'] for c in x['children']] for x in before]
    with pytest.raises(RuntimeError, match='Injected stop'):
        merge_group(mcp, directory / 'operation', f['keys'], inject='after_prepare')
    assert read_json(directory / 'operation/merge.json')['state'] == 'prepared'
    assert merge_group(mcp, directory / 'operation', f['keys'], recover=True)['restored']
    restored = tree(mcp, f['keys'], 1)
    assert [[c['key'] for c in x['children']] for x in restored] == [[c['key'] for c in x['children']] for x in before]
    with pytest.raises(RuntimeError, match='Injected stop after native commit'):
        merge_group(mcp, directory / 'operation', f['keys'], inject='after_native')
    with pytest.raises(RuntimeError, match='Injected finalization rollback'):
        merge_group(mcp, directory / 'operation', f['keys'], inject='finish')
    result = merge_group(mcp, directory / 'operation', f['keys'])
    assert result['passed'] and result['preserved_child_keys'] == 8
    assert merge_group(mcp, directory / 'operation', f['keys']) == result
    snap = mcp.snapshot(f['keys'][0])
    assert snap['item']['abstractNote'] == '合并后补齐的摘要'
    assert len(snap['item']['collections']) == 2
    assert len(snap['attachments']) == 4
    assert len(snap['notes']) == 3  # Two originals plus conflict audit.


def _item(i, title):
    return dict(key=f'K{i:04d}', itemType='journalArticle', DOI='', title=title, date='', dateAdded='2024', creators=[])


def _brute_review(items):
    """Frozen-baseline reference: the pre-optimization exact scan, with its loose length gate."""
    import difflib
    from zotero_skills.dedup import normalized
    out = []
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            ta, tb = normalized(a.get('title')), normalized(b.get('title'))
            if min(len(ta), len(tb)) >= 15 and difflib.SequenceMatcher(None, ta, tb).ratio() >= .9:
                out.append((a['key'], b['key']))
    return sorted(out)


def test_review_scan_is_equivalent_to_frozen_baseline_scan():
    import random
    import string
    random.seed(11)
    words = [''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 10))) for _ in range(400)]
    items = []
    for n in range(400):
        title = ' '.join(random.choices(words, k=random.randint(5, 12)))
        if items and random.random() < .15:  # near-duplicates of earlier titles
            base = items[random.randrange(len(items))]['title']
            title = base if random.random() < .5 else base + ' ' + random.choice(words)
        items.append(_item(n, title))
    from zotero_skills.dedup import normalized
    from zotero_skills import lossless_qgram
    keys = [x['key'] for x in items]
    pairs = lossless_qgram.review_pairs([normalized(x['title']) for x in items], exclude_pair=lambda i, j: False)
    got = sorted((keys[p.i], keys[p.j]) for p in pairs)
    assert got == _brute_review(items)


def test_review_scan_covers_repeated_gram_and_asymmetric_pairs():
    from zotero_skills import lossless_qgram
    # 52 shared repeated 3-grams but only one shared distinct gram: multiset, not set.
    items = [_item(0, 'a' * 54 + 'bcdefg'), _item(1, 'a' * 54 + 'hijklm')]
    assert len(groups(items)[1]) == 1
    # difflib asymmetry: ratio(diet,tide)=0.90 but ratio(tide,diet)=0.85.
    # The scan must keep the original i<j argument direction, so this hits...
    items = [_item(0, 'x' * 16 + 'diet'), _item(1, 'x' * 16 + 'tide')]
    assert len(groups(items)[1]) == 1
    # ...and the reverse order must not gain a hit by flipping arguments.
    items = [_item(0, 'x' * 16 + 'tide'), _item(1, 'x' * 16 + 'diet')]
    assert len(groups(items)[1]) == 0


def test_review_scan_results_are_deterministic():
    import random
    import string
    titles = ['quantum capacitance of carbon nanotubes in ionic liquids',
              'quantum capacitance of carbon nanotubes in ionic liquid',
              'dynamic density functional theory of fluids',
              'dynamic density functional theory of fluid',
              'a completely unrelated title about photosynthesis mechanisms']
    items = [_item(i, t) for i, t in enumerate(titles)]
    first = [(x['keys']) for x in groups(items)[1]]
    second = [(x['keys']) for x in groups(items)[1]]
    assert first == second and len(first) >= 2
