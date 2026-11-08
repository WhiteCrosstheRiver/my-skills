---
name: book-distiller
description: 把一本书(Zotero 里的书,或本地 EPUB/PDF)蒸馏成独立、可阅读、可导航、可检索、可回溯的阅读 HTML(原文为主干 + AI 导读/边注/概念卡/自测)。当用户说"把某本书做成阅读 HTML / 蒸馏这本书 / book html / 书籍蒸馏"时使用。不用于论文(论文用 zotero-skills 的 distill)。
---

# Book Distiller — 书籍 → 蒸馏阅读 HTML

> **原文是主干,蒸馏是增强层。** AI 内容不得打断原书阅读、不得让读者失去"我在原书哪里"。
> **没读过的段落不写边注。** 每条边注都要带一句它所钉住段落里的原文 `quote`,校验器逐条核对。

脚本都在 `book-distiller/`(下文 `<bd>`)。需要 Python 3.11+ 和 `pymupdf`(PDF 才需要)。所有命令输出 UTF-8。

## 流程(按顺序,不跳步)

### 1. 找书并抽取 Book IR

```bash
python <bd>/bookir.py zotero-list --query "悉达多"           # 读本机 Zotero(只读快照),列出带 EPUB/PDF 的书
python <bd>/bookir.py zotero-extract <ITEM_KEY> <work>/ir      # 同一本书有 EPUB 时优先 EPUB
python <bd>/bookir.py extract <book.epub|book.pdf> <work>/ir   # 非 Zotero 的本地文件
```

- 输出最后一段是 JSON 质量报告。**先看 `warnings`,再决定是否继续**:
  - `giant_paras` > 0 或 "one chapter holds >70%" → 结构没恢复好,告诉用户,别硬蒸馏;
  - `ok:false` / 退出码 3 → 扫描件(需 OCR)、文字太少、乱码。**诚实失败,写明原因,绝不编造正文。**
  - `equation/figure heavy` → 教材类 PDF 的公式/图表文字层碎片已合并为 `(formula/figure fragments)` 段(阅读器里小号灰字)。**这些段不可当公式读:不引用、不解释其中的数学内容**,讲公式只依据前后的文字说明,并在导读里注明公式需看原书。
  - OCR 文字层的错字(如 `eveiything`)属于原文:`quote` 照抄,不要"修正",否则校验不通过。
  - 附件显示 `(missing)` = 文件在 Zotero 同步服务器上没下到本机:请用户在 Zotero 里打开一次该附件(或修复 文件同步 凭据),不要自己去网上找盗版。
- AZW3/MOBI 先用 calibre `ebook-convert` 转 EPUB。

### 2. 通读,而不是抽样

```bash
python <bd>/read_ir.py outline <work>/ir                  # 章节表、每章段数/字数、质量警告
python <bd>/read_ir.py chapter <work>/ir <ch>             # 整章带编号输出 [章.段];太长会提示 --from 续读
python <bd>/read_ir.py find <work>/ir "某个词"             # 查原文精确位置(概念名/引文必须是原文子串)
```

`[3.17]` = 第 3 章(0 起)第 17 段(0 起),与 distill 里的下标完全一致。**一章没读完,不写这一章的 part。**

### 3. 逐章写蒸馏 part(可断点续跑)

每读完一章,立刻写 `<work>/parts/ch-NNN.json`(NNN = 章下标三位补零),然后再读下一章。上下文不够或会话掉线时,已写好的 part 不丢,从下一个缺失的章继续。

```json
{"chapter": 3,
 "entry": {"q": "这一章要回答什么(一句话问题)",
           "route": ["4–8 个关键词组成的知识路线"],
           "keys": [{"text": "关键点(可跳转)", "at": 17}, "关键点"],
           "motif": "可选:一句补充", "time": 12},
 "notes": [{"at": 17, "tag": "KEY", "text": "一句话提炼", "deeper": "可选展开",
            "quote": "第17段里的一句原文,逐字复制"}],
 "quiz": [{"q": "问题", "a": ["A", "B", "C"], "correct": 1, "fb": "解析,指回原文 ¶"}],
 "concepts": [{"id": "ascii-id", "name": "原文里逐字出现的词", "en": "", "one": "一句话", "first": [3, 17], "rel": ["相关概念"]}]}
```

书级信息写 `<work>/parts/book.json`:`{"subtitle": "作者 / 译者 · 一句话副题", "concepts": [...]}`。

**蒸馏规范**

- 章导读:每个实质章节(≥1500 字)都要有;`q` 是这一章真正在回答的问题,不是章节名复述。
- 边注:每章 2–8 条,**分布在全章**(只钉在前 40% 会被警告:说明后面没读);tag 用 `KEY / SECTION DISTILLED / REASONING BRIDGE / COMMON PITFALL / CONNECTION / MOTIF / CHARACTER / IMAGE / ARGUMENT / EVIDENCE / METHOD / ACTION / COUNTERPOINT`。边注讲"为什么重要 / 和哪里呼应 / 容易误读什么",不复述段落。
- 概念卡:全书 8–25 张;`name` 必须是原文逐字子串(否则 hover 永远不触发);同名概念在后续章只补 `rel`。
- 自测:可选,每章 0–2 题,答案能在原文找到。
- 小说:母题 / 人物 / 意象 / 结构,**不写剧情复述**;非虚构:核心论点、论证链、方法、可行动建议、反例与边界。
- 全部中文(英文书可中英并列)。不编造引文、不编造页码、不引入书外"事实"冒充书中内容;书外背景用 `CONTEXT` tag 明示。

### 4. 合并 + 校验

```bash
python <bd>/check_distill.py merge <work>/ir <work>/parts <work>/distill.json
```

- `errors` 必须为 0:下标越界、quote 不在该段(编造或意译)、概念名不是原文子串、缺字段。按提示修 part 后重新 merge。`--fix` 只做机械修正(把 quote 重新钉到它真正所在的段、修 `first`、估算阅读时间)。
- `warnings` 是覆盖度问题(实质章节缺导读/边注、边注扎堆、概念过少):尽量补齐;确实不需要的在汇报里说明。

### 5. 渲染 + 验收

```bash
python <bd>/build_book.py <work>/ir <work>/distill.json "<Desktop>/<书名>.html" "<书名>"
```

- 构建前自动复跑校验,有 error 拒绝构建。旧版(v1,无 quote)蒸馏稿用 `--legacy`。
- 图片总量 ≤2MB 内联成单文件;更大时写到 HTML 旁的 `assets/<书名>/`,**两者要一起移动**。
- 验收:打开 HTML,切三层(Original / Enhanced / Study),确认:TOC 跳转与小节高亮、边注不压正文、概念 hover、Ctrl+K 搜索、选中文字高亮后刷新仍在。

## 汇报

告诉用户:书名与来源(Zotero key / 文件)、抽取质量(章/段/图、警告)、蒸馏覆盖(导读 x/实质章节 y、边注数、概念数、自测数)、未处理的问题、HTML 路径。

## 大批量(整库)

- 一本书一个工作目录;`parts/` 天然断点续跑。用 `check_distill.py merge` 的 `ok` 作为"这本书完成"的唯一标准。
- 免费档模型线程不稳定:**同一时间只跑一个蒸馏线程**,掉线后从缺失的 `ch-NNN.json` 继续,不要并发重试。
- 失败要诚实:扫描件、DRM、只有目录、正文是广告 → 记录原因,跳过。

## 渲染风格(build_book.py 已实现,改样式时遵守)

配色:页面底 `oklch(0.915 0.007 80)`,纸面 `oklch(0.998 0.002 85)`,AI 蓝 `oklch(0.935 0.035 250)` / 字 `oklch(0.22 0.05 250)`,高亮 `oklch(0.89 0.14 92)`,书签 `oklch(0.62 0.13 60)`。字体 Noto Serif SC(正文 1.95 行高、首行缩进)/ Noto Sans SC(UI)/ IBM Plex Mono(编号)。布局:52px header + 264px TOC + 760px 纸面 + 46px footer。所有 AI 内容带 `AI ·` 小标,Original 层完全隐藏。

## 版权

生成的 HTML 含书籍全文,仅限用户本机个人使用,不公开分发;仓库里不提交 IR、蒸馏稿或 HTML。
