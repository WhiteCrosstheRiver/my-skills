# Detailed per-paper analysis

Read evidence.json and the **whole** page-labeled fulltext.txt before analyzing an available paper. Check actual PDF identity against metadata. Extra PDFs may be supplements; preserve their source keys. User annotations are context, not automatically the paper's conclusions. If code is relevant, inspect its real repository/documentation read-only and append fetched source text, URL and retrieval time to `external_sources` in evidence.json before computing source_hash. Never execute downloaded repository code as part of note generation.

`note-template --run PATH --paper ID` creates an explicitly unfinished draft and will not overwrite an existing note. Fill all 13 sections. Match the supplied sample's depth: explain study logic, equations and symbols, procedures, controls, materials, data splits, parameters with units, quantitative comparisons and limits. Include affiliations only when sourced. For code report repository URL, version/license when found, reusable components and whether reproduction was actually tested. Do not call untested code “verified” or infer author roles from name order.

Frontmatter: schema, item_key, library_id, doi, evidence_level, status, generated_at, source_hash, analyst. Set `status: complete` only after real analysis. The source hash is SHA256 of `json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode('utf-8')`. Evidence levels: `fulltext`, `abstract`, `metadata`. Missing facts should say 未报告/未验证/全文不可得. Fulltext unavailable notes must not infer experimental parameters from a title or abstract.

**作者与团队检索（必做）**：作者与团队背景直接决定综述中的文献权重，蒸馏时必须用宿主的检索工具调查通讯作者与核心作者：所属课题组的规模与方向、在本文领域的代表性工作、是否为大型/高影响力团队（如长期维护本文所述的软件、方法或数据集）。每条检索到的信息都要先把网页文本（含 URL 和检索时间）追加进 evidence.json 的 `external_sources`（如 `{"id": "E1", "url": "...", "title": "...", "retrieved_at": "...", "text": "..."}`），重算 source_hash 后才能在 claims.json 里以该 ID 引用；摘录会被逐字校验。团队声望的判断写为 `inference` 并区分于网页原文 `reported`；查不到的信息写 未报告/未验证，不得虚构头衔、h 指数或团队规模。

Required second-level sections: 文献身份与摘要；背景与研究问题；核心贡献；实验与论证思路；关键方法与过程；公式与参数；结果与对照；结论与适用边界；局限与矛盾；作者与团队；代码、数据与复现；研究启发；证据索引与生成记录。

Use inline evidence IDs such as `[C1]` alongside important claims. Save claims.json:

```json
[
  {"id":"C1","kind":"reported","statement":"Your accurate paraphrase", "evidence":[{"source":"PDF_ATTACHMENT_KEY","page":3,"excerpt":"A short exact passage from that page"}]}
]
```

Kinds: reported, inference, limitation, metadata. Sources: a PDF attachment key + page, `abstract`, `metadata`, or an explicitly stored external_source ID. Excerpts must exist verbatim after whitespace normalization; keep quotes short. Automated matching checks provenance, not entailment: independently check that each cited source supports the **actual numeric/directional claim**, and distinguish your inference from authors' claims.

Publish with `publish-note --run PATH --paper ID`. It validates the note, creates an immutable child-note version, attaches Markdown, reads it back and archives source/provenance. Repeating identical content reuses the same version; a human edit to a tagged note is preserved and a new version is created. Complete all selected papers before reporting the whole run complete.
