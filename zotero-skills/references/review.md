# 证据驱动的版本化综述

准备：`zotero-skill review --title "领域综述" --source-run PATH`，可多次指定 source-run；也可按 `--collection KEY` 或 `--topic "短语"` 读取本机已发布笔记档案。仅纳入已完成并验证的笔记，不能把等待分析的条目当成精读输入。

先阅读 `matrix.json` 的问题—方法—结果—证据等级—冲突矩阵及 `sources/KEY/` 完整笔记。按实际领域组织长篇章节，避免逐篇摘要拼接：比较可比的对照、区分材料/数据/硬件/版本条件、保存冲突和未解决问题。结果外推必须明确是分析者推断。

编写 `review.md`：一级标题及若干 `##` 章节，公式用 `$...$`/`$$...$$`，事实段落与比较表标记 `[R1]` 等。另写 `review-claims.json` 数组：`{"id":"R1","statement":"可核查的综合结论","kind":"reported|synthesis|limitation","refs":["ITEMKEY:C1"]}`。refs 必须指向纳入笔记的真实 claim，复杂综合应有多文献支持。不能跨不同指标或基准直接排名。

请独立审查正文与证据，重点检查数值、单位、方法遗漏和过度解释。审查通过后保存 `audit.json`：`status: passed`、`reviewer`、`draft_hash`（review.md 读取为UTF-8文本、统一LF后的SHA256）、`review_hash`（调用 `review.audit_hash(run)`，绑定正文、声明、来源版本）、`checks` 列表；有阻断项先修稿再复审。自动验证只能核对引用存在，不能代替语义审查。

发布：`zotero-skill review --publish --run PATH`。生成 Markdown、离线 HTML、KaTeX本地资源、比较矩阵、证据清单、版本清单及变化记录；Zotero 中保存 report 条目、阅读便条、Markdown 和完整离线 ZIP。每次正文/输入版本变化生成新时间戳目录；再次发布相同任务复用，不覆盖历史。任务中断可用 resume 继续。

更新时重新准备源笔记，沿用相同 title；报告新增/移出论文、笔记版本变化、综合声明变化与未决争议。版本目录完整复制可离线查看，单独复制 HTML 会缺少字体及证据文件。
