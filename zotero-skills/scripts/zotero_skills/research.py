"""Research planning and coverage diagnostics; scholarly judgments stay with the host."""
from collections import Counter

from .core import now, read_json, write_json


def load_plan(path):
    plan = read_json(path)
    facets = plan.get('facets') if isinstance(plan, dict) else None
    if not isinstance(facets, list) or not facets:
        raise ValueError('Search plan requires facets [{name, queries:[...]}]')
    queries, names = [], set()
    for facet in facets:
        if not isinstance(facet, dict) or not isinstance(facet.get('name'), str) or not facet['name'].strip():
            raise ValueError('Each facet needs a name')
        if facet['name'] in names:
            raise ValueError('Duplicate facet name')
        names.add(facet['name'])
        values = facet.get('queries')
        if not isinstance(values, list) or not values or any(not isinstance(q, str) or not q.strip() for q in values):
            raise ValueError('Each facet needs nonempty query strings')
        facet['queries'] = list(dict.fromkeys(q.strip() for q in values))
        queries.extend(facet['queries'])
    return plan, list(dict.fromkeys(queries))


def request_plan(run):
    """Do not pretend that appending generic words translates or maps a domain."""
    plan = {'topic': run.state['config']['topic'], 'scope': '', 'questions': [],
            'facets': [{'name': name, 'queries': []} for name in
                       ['概念与奠基', '主要方法', '应用场景', '比较与基准', '局限与反例', '近期进展']],
            'stop_rule': '重要问题均有可用证据；连续扩展不再增加重要分支，或达到明确时间/篇数预算；记录未完成项。'}
    write_json(run.path / 'search-plan.json', plan)
    run.state['status'] = 'awaiting_query_plan'
    run.save()
    return {'run': str(run.path), 'status': run.state['status'], 'plan': str(run.path / 'search-plan.json'),
            'next': 'Host: map the domain to research questions, terminology (including English aliases), method families and competing evidence. Fill search-plan.json facets with short queries, then resume --run PATH --plan PATH/search-plan.json --discover. This template is not a completed search.'}


def coverage(run):
    """Counts describe retrieval, not semantic relevance or exhaustive coverage."""
    config = run.state['config']
    candidates = run.state.get('candidates', [])
    papers = run.state.get('papers', [])
    screening = screening_summary(run)
    tasks = list(run.state.get('search_tasks', {}).values())
    facets = []
    for facet in config.get('search_plan', {}).get('facets', []):
        queries = set(facet['queries'])
        hits = [p for p in candidates if any(isinstance(s, dict) and s.get('query') in queries for s in p.get('sources', []))]
        ids = {p['id'] for p in hits}
        selected = [p for p in papers if p['id'] in ids]
        facets.append({'name': facet['name'], 'queries': facet['queries'], 'retrieved': len(hits),
                       'selected': len(selected), 'fulltext': sum(p.get('evidence_level') == 'fulltext' for p in selected),
                       'candidate_ids': sorted(ids)})
    warnings = []
    if screening['unassessed'] or screening['deferred']:
        warnings.append(f"尚有 {screening['unassessed']} 篇未筛选、{screening['deferred']} 篇暂缓；入选子集完成不等于领域研究完成。")
    if len(config.get('queries') or [config.get('topic')]) < 2:
        warnings.append('仅一个检索式；领域覆盖不足，补充英文术语、方法、应用和反例检索。')
    if any(t['status'] == 'failed' for t in tasks):
        warnings.append('有检索失败；失败不能视作零命中，用 resume --discover 重试。')
    if any(t['status'] == 'failed' for t in run.state.get('citation_tasks', {}).values()):
        warnings.append('有引文扩展失败；已完成方向保留，resume --snowball 重试未完成方向。')
    if any(t.get('possibly_truncated') for t in tasks):
        warnings.append('有检索达到抓取上限；用更具体检索式分拆，或提高 --candidate-limit 后重试。')
    if any(f['retrieved'] == 0 for f in facets):
        warnings.append('有研究分支没有候选；改写该分支检索式，不能据此认定没有研究。')
    pending = [s for s in run.state.get('host_searches', []) if s.get('status', 'pending') == 'pending']
    if pending:
        warnings.append('浏览器协作检索尚未完成或未记录状态；生成链接不代表已经检索。')
    if papers and not any(p.get('evidence_level') == 'fulltext' for p in papers):
        warnings.append('尚无已取得全文的条目；不足以写机制、定量比较和深入综述。')
    data = {'schema': 1, 'at': now(), 'topic': config.get('topic'), 'candidates': len(candidates),
            'selected': len(papers), 'evidence': dict(Counter(p.get('evidence_level', 'pending') for p in papers)),
            'screening': screening, 'tasks': tasks, 'facets': facets, 'host_pending': len(pending), 'warnings': warnings}
    write_json(run.path / 'coverage.json', data)
    lines = ['# 检索与证据覆盖', '', f"候选 {len(candidates)}；入选 {len(papers)}。下列命中仅表示来源检索命中，相关性由阅读筛选确认。", '']
    lines += ['- ' + w for w in warnings]
    lines += ['', '| 分支 | 候选 | 入选 | 全文 |', '|---|---:|---:|---:|']
    lines += [f"| {f['name']} | {f['retrieved']} | {f['selected']} | {f['fulltext']} |" for f in facets]
    lines += ['', '| 来源 | 检索式 | 状态 | 返回 | 新增 | 达到上限 |', '|---|---|---|---:|---:|---|']
    lines += [f"| {t['provider']} | {t['query'].replace('|', '/')} | {t['status']} | {t.get('count', '—')} | {t.get('new_unique', '—')} | {t.get('possibly_truncated', False)} |" for t in tasks]
    (run.path / 'coverage.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return data


def screening_summary(run):
    known = {p['id'] for p in run.state.get('candidates', [])}
    path = run.path / 'selection.json'
    selected = read_json(path) if path.exists() else {}
    groups = {name: {r['id'] for r in selected.get(name, []) if r.get('id') in known}
              for name in ('included', 'excluded', 'deferred')}
    groups['included'].update(p['id'] for p in run.state.get('papers', []) if p['id'] in known)
    unassessed = known - set.union(*groups.values())
    return {'candidates': len(known), **{k: len(v) for k, v in groups.items()},
            'unassessed': len(unassessed), 'unassessed_ids': sorted(unassessed)}


def completion_status(run):
    screening = screening_summary(run)
    return 'selected_complete_scope_pending' if screening['unassessed'] or screening['deferred'] else 'complete'


def screening_batch(run, size=40, decisions=None):
    """A reading batch is not an inclusion cap; retain full abstracts and provenance."""
    if size < 1:
        raise ValueError('Batch size must be positive')
    if decisions:
        path = run.path / 'selection.json'
        prior = read_json(path) if path.exists() else {}
        updates = read_json(decisions)
        if not isinstance(updates, dict) or not any(updates.get(k) for k in ('included', 'excluded', 'deferred')):
            raise ValueError('Supply included/excluded/deferred decision lists')
        known = {p['id'] for p in run.state.get('candidates', [])}
        imported = {p['id'] for p in run.state.get('papers', [])}
        merged = {p['id']: (group, p) for group in ('included', 'excluded', 'deferred') for p in prior.get(group, [])}
        seen = set()
        for group in ('included', 'excluded', 'deferred'):
            for row in updates.get(group, []):
                ident = row.get('id')
                if ident not in known or ident in seen or not str(row.get('reason', '')).strip():
                    raise ValueError('Decisions require unique known IDs and reasons')
                if ident in imported and group != 'included':
                    raise ValueError('Cannot remove earlier inclusions; create a new scoped run')
                merged[ident] = (group, row)
                seen.add(ident)
        write_json(path, {g: [r for group, r in merged.values() if group == g] for g in ('included', 'excluded', 'deferred')})
        coverage(run)
    summary = screening_summary(run)
    pending = set(summary['unassessed_ids'])
    rows = [p for p in run.state.get('candidates', []) if p['id'] in pending][:size]
    path = run.path / 'screening-batch.json'
    write_json(path, rows)
    return {'batch': str(path), 'batch_count': len(rows), 'unassessed': len(pending),
            'remaining_after_batch': len(pending) - len(rows),
            'next': 'Read every full abstract; inspect sources when ambiguous. Save batch decisions as included/excluded/deferred lists with reasons, then screening-batch --decisions FILE merges them without Zotero writes and returns the next batch. After screening, resume --selection PATH/selection.json imports cumulative inclusions. This batch file is not a completed decision.'}
