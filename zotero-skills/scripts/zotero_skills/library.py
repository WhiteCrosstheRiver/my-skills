"""Snapshot enumeration: fixed identities first, paged reads second."""
from .core import write_json


def enumerate_items(mcp, library=1, collection=None, topic=None, page_size=100):
    if page_size < 1:
        raise ValueError('page_size must be positive')
    keys = mcp.js("""
let collections=null;
if(P.collection){const root=await Zotero.Collections.getByLibraryAndKeyAsync(P.library,P.collection);if(!root)throw new Error('Collection missing');collections=new Set([root.id,...Zotero.Collections.getByParent(root.id,true).map(c=>c.id)]);}
const s=new Zotero.Search();s.libraryID=P.library;s.addCondition('itemType','isNot','attachment');s.addCondition('itemType','isNot','note');
const items=await Zotero.Items.getAsync(await s.search());
return items.filter(x=>x.isRegularItem()&&!x.deleted&&(!collections||x.getCollections().some(id=>collections.has(id)))&&(!P.topic||[x.getField('title'),x.getField('abstractNote'),...x.getTags().map(t=>t.tag)].join(' ').toLowerCase().includes(P.topic.toLowerCase()))).map(x=>x.key).sort();
""", library=library, collection=collection, topic=topic)
    result = []
    for offset in range(0, len(keys), page_size):
        result.extend(mcp.js("""
return await Promise.all(P.keys.map(async k=>{const x=await Zotero.Items.getByLibraryAndKeyAsync(P.library,k);if(!x||x.deleted)throw new Error('Library changed during enumeration: '+k);return x.toJSON();}));
""", library=library, keys=keys[offset:offset + page_size]))
    if len(result) != len(set(keys)):
        raise RuntimeError('Enumeration incomplete')
    return result
