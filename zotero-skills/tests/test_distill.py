import os
import uuid

import pytest

from zotero_skills.core import MCP, Network, Run, default_output, read_json, write_json
from zotero_skills.distill import process
from zotero_skills.library import enumerate_items
from zotero_skills.notes import note_template, publish


@pytest.mark.skipif(os.environ.get('ZOTERO_SKILLS_LIVE') != '1', reason='Opt-in labelled synthetic items')
def test_live_nested_pagination_shared_items_and_resume():
    mcp = MCP()
    fixture = mcp.js("""
const result={keys:[]};await Zotero.DB.executeTransaction(async()=>{
const root=new Zotero.Collection();root.libraryID=1;root.name='Zotero Skills Tests - Distill '+P.token;await root.save();result.collection=root.key;
const sub=new Zotero.Collection();sub.libraryID=1;sub.name='子收藏夹';sub.parentID=root.id;await sub.save();
const sub2=new Zotero.Collection();sub2.libraryID=1;sub2.name='第三层';sub2.parentID=sub.id;await sub2.save();
for(let i=0;i<105;i++){const x=new Zotero.Item('journalArticle');x.libraryID=1;x.setField('title','[TEST] 蒸馏分页 '+P.token+' '+i);x.setField('abstractNote','合成验收条目，没有论文全文，不作任何科学结论。');x.addToCollection(i%2?sub.id:sub2.id);if(i%3===0)x.addToCollection(root.id);await x.save();result.keys.push(x.key);if(i===0){const n=new Zotero.Item('note');n.libraryID=1;n.parentItemID=x.id;n.setNote('<p>人工备注需要保留并提供给精读者。</p>');await n.save();result.note=n.key;}}
});return result;
""", token=uuid.uuid4().hex[:8])
    rows = enumerate_items(mcp, 1, fixture['collection'], page_size=17)
    assert len(rows) == 105 and {r['key'] for r in rows} == set(fixture['keys'])
    run = Run.create(default_output() / 'validation', 'distill', {'library': 1, 'collection': fixture['collection']})
    run.state['papers'] = [{'id': r['key'], 'item_key': r['key'], 'title': r['title'], 'status': 'selected', 'pdf_urls': []} for r in rows]
    run.save()
    class StopAfterFirst:
        def __init__(self): self.calls = 0
        def snapshot(self, *args, **kwargs):
            self.calls += 1
            if self.calls > 1: raise KeyboardInterrupt('Simulated process interruption')
            return mcp.snapshot(*args, **kwargs)
    net = Network(default_output() / 'cache')
    with pytest.raises(KeyboardInterrupt): process(run, StopAfterFirst(), net)
    assert Run(run.path).state['papers'][0]['status'] == 'awaiting_analysis'
    result = process(Run(run.path), mcp, net)
    assert result['total'] == result['awaiting_analysis'] == 105
    p = next(p for p in run.state['papers'] if p['item_key'] == fixture['keys'][0])
    e = read_json(run.paper_dir(p) / 'evidence.json')
    assert e['level'] == 'abstract' and e['fulltext_status'] == 'unavailable'
    assert any(n['key'] == fixture['note'] for n in e['user_notes'])
    assert '人工备注' in next(n['html'] for n in mcp.snapshot(p['item_key'])['notes'] if n['key'] == fixture['note'])
    directory = run.paper_dir(p)
    note = note_template(e).replace('status: draft', 'status: complete').replace('待填写：依据 evidence.json，缺失信息明确说明。', '合成测试记录，全文不可得；本节没有学术证据，不推断论文事实。[C1]')
    (directory / 'note.md').write_text(note, encoding='utf-8')
    write_json(directory / 'claims.json', [{'id': 'C1', 'kind': 'metadata', 'statement': '测试记录无全文', 'evidence': [{'source': 'abstract', 'excerpt': '合成验收条目，没有论文全文'}]}])
    publication = publish(Run(run.path), p['id'], mcp)
    again = publish(Run(run.path), p['id'], mcp)
    assert publication['note_key'] == again['note_key']
    assert any(n['key'] == fixture['note'] for n in mcp.snapshot(p['item_key'])['notes'])
