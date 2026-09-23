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
