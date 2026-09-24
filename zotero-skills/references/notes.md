# Detailed per-paper analysis

Read evidence.json and the **whole** page-labeled fulltext.txt before analyzing an available paper. Check actual PDF identity against metadata. Extra PDFs may be supplements; preserve their source keys. User annotations are context, not automatically the paper's conclusions. If code is relevant, inspect its real repository/documentation read-only and append fetched source text, URL and retrieval time to `external_sources` in evidence.json before computing source_hash. Never execute downloaded repository code as part of note generation.

`note-template --run PATH --paper ID` creates an explicitly unfinished draft and will not overwrite an existing note. Fill all 13 sections. Match the supplied sample's depth: explain study logic, equations and symbols, procedures, controls, materials, data splits, parameters with units, quantitative comparisons and limits. Include affiliations only when sourced. For code report repository URL, version/license when found, reusable components and whether reproduction was actually tested. Do not call untested code “verified” or infer author roles from name order.

Frontmatter: schema, item_key, library_id, doi, evidence_level, status, generated_at, source_hash, analyst. Set `status: complete` only after real analysis. The source hash is SHA256 of `json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode('utf-8')`. Evidence levels: `fulltext`, `abstract`, `metadata`. Missing facts should say 未报告/未验证/全文不可得. Fulltext unavailable notes must not infer experimental parameters from a title or abstract.

**作者与团队检索（必做，但与证据等级分离）**：用宿主检索工具调查通讯/核心作者的课题组、领域代表作、与本文软件/方法/数据集的维护关系；每条信息先把网页文本（含 URL 与检索时间）追加进 evidence.json 的 `external_sources`（`{"id": "E1", "url": "...", "title": "...", "retrieved_at": "...", "text": "..."}`），重算 source_hash 后才能以该 ID 引用（摘录逐字校验）。区分**方法开发、合作应用、外部采用与独立复现**四种角色。团队规模、名望、期刊与被引量是背景资料，**不得直接提高科学声明的证据等级**——它们只影响综述中的组织权重，不改变 claim 的 kind 与证据强度。查不到写 未报告/未验证，不得虚构头衔、h 指数或团队规模。

**蒸馏质量：保留推理依据，而非仅压缩摘要**。笔记的目标是生成可供跨文献分析复用的证据记录；不得以篇幅、栏目填满、作者影响力或引用数代替分析完成度。

- **来源与版本**：识别论文、预印本各版本、正式发表版、补充材料、数据与代码之间的关系；记录实际使用的来源版本。发现正式版与所读版本不同，报告差异，不得静默替换书目信息或混写不同版本的结果。
- **内容覆盖**：写笔记前建立覆盖记录——「已读取文字」「已检查图表」「已核对代码」「已实际复现」分别记录，不得互相替代；缺失部分明确写未取得、未检查或未报告（可记在证据索引栏或宿主自建的辅助记录，不强求新文件格式）。
- **读前分诊（记法随文体）**：实证/计算型文章抓研究问题、（显式或隐式的）假设、方法与测量、关键发现四要素；理论/综述型文章抓主旨、支撑论证的组成、框架的核心命题。两种文体都有：将来可引用的观点、可复用的方法、设计上的不足与改进设想、让你想到的同类或相反结论的其他文献、你自己的 critique——这些记入「研究启发」与「局限与矛盾」，不代替论文内容。
- **方法解释**：核心方法保留输入与输出、关键步骤、关键公式及符号、参数作用、假设、相对基线的具体变化、可复用部分和必要验证；方法名与软件名不能替代过程解释。
- **原子化声明**：每条 claim 尽量对应一个可独立判断真假的命题；区分直接结果、作者解释、分析者推断和待验证假设；保留作者原有的条件、比较对象和不确定措辞，不得增强结论强度。
- **数字与证据**：数字必须绑定指标定义、单位、对象、实验/计算条件及来源位置。表格证据需覆盖行列、表头、单位和必要脚注；图形证据需实际检查图例、坐标轴、误差定义和相关正文——仅有图表标题，不得标记为数值已核验。
- **边界与反证**：明确记录作者承认的局限、观察到的失败、可能的替代解释、未检验范围，以及不能由本结果推出的结论。没有发现反例不等于不存在反例；不强行编造争议。
- **审查**：关键结论的核验必须回到原始来源（原文页/表/图/代码），不得仅对照自己生成的摘要；证据不足时降低措辞或标记待核验，不得用无关引用补齐。

Required second-level sections: 文献身份与摘要；背景与研究问题；核心贡献；实验与论证思路；关键方法与过程；公式与参数；结果与对照；结论与适用边界；局限与矛盾；作者与团队；代码、数据与复现；研究启发；证据索引与生成记录。

Use inline evidence IDs such as `[C1]` alongside important claims. Save claims.json:

```json
[
  {"id":"C1","kind":"reported","statement":"Your accurate paraphrase", "evidence":[{"source":"PDF_ATTACHMENT_KEY","page":3,"excerpt":"A short exact passage from that page"}]}
]
```

Kinds: reported, inference, limitation, metadata. Sources: a PDF attachment key + page, `abstract`, `metadata`, or an explicitly stored external_source ID. Excerpts must exist verbatim after whitespace normalization; keep quotes short. Automated matching checks provenance, not entailment: independently check that each cited source supports the **actual numeric/directional claim**, and distinguish your inference from authors' claims.

Publish with `publish-note --run PATH --paper ID`. It validates the note, creates an immutable child-note version, attaches Markdown, reads it back and archives source/provenance. Repeating identical content reuses the same version; a human edit to a tagged note is preserved and a new version is created. Complete all selected papers before reporting the whole run complete.
