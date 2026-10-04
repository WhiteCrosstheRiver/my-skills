---
name: book-distiller
description: 把 Zotero 里的任意书籍(EPUB/PDF)蒸馏成一个独立、可阅读、可导航、可检索、可回溯的书籍阅读 HTML(Structured Distilled Book)。当用户要求"把某本书做成阅读 HTML / 蒸馏书籍 / book html"时使用。
---

# Book Distiller — 书籍 → 蒸馏阅读 HTML

把一本"线性文件"(EPUB/PDF)重新编译成一个**知识对象**。

## 核心原则(不可违背)

> **原文是主干,蒸馏是增强层。任何 AI 内容不得打断原书阅读,不得让读者失去"我在原书哪里"的感觉。**

- HTML 内部**不依赖 PDF/EPUB**——它们只是一次性输入。中间产物是 Book IR(见下)。
- 原文与 AI 内容**视觉隔离**:白底 = 原书;淡蓝 `oklch(0.935 0.035 250)` 侧栏/卡片 = AI;所有 AI 内容必须带 `AI ·` 小标。
- 默认干净阅读,蒸馏按需展开(Original / Enhanced / Study 三层)。

## 流水线

```
EPUB/PDF → Parser(结构恢复) → Book IR → AI Distillation → Enhanced IR → HTML Renderer → book.html
```

### 1. Book IR(先于一切 UI;存到 `<book>/ir/`)

```
book.json          # 元数据: title, author, translator, source(如 Zotero storage key)
chapters/ch*.json  # [{type: paragraph|heading|quote|..., text, id: p-XXX}]
distill/           # chapter_entry(章导读), section_summary, concepts(概念卡)
```

- 每个段落有稳定锚点 `id`(如 `p-003-018`),用于 TOC 跳转 / Scroll Spy / 高亮 / 笔记。
- 概念卡 schema:`{id, name, en, one(一句话), first(首次出现锚点), related[]}`。

### 2. 解析 EPUB

- `unzip` 到临时目录,按 OPF spine 顺序读 XHTML,`python + lxml/regex` 抽文本。
- 章节以 spine 文件为界;每章内按自然段编号。

### 3. 蒸馏层(每章必做)

- **章导读(Chapter Entry)**:这一章要回答什么 / 知识路线(关键词链) / 3 个关键点(带锚点跳转) / 阅读时间估计。
- **小节边注(Section margin notes)**:每章 3–8 条 `AI · SECTION DISTILLED / ¶x.x KEY / REASONING BRIDGE / COMMON PITFALL / CONNECTION`,若干条带 "Deeper ▸" 展开或 "Why? 为什么" 按钮。
- **概念卡(Concept Registry)**:人名/术语/意象;正文中可 hover 的词用 `<span class="term" data-term="...">` 标注(Enhanced 层显示)。

### 4. HTML Renderer(单一 self-contained 文件,全部内联)

**风格必须复刻** `Downloads/_book_design_ref/Book Reader.dc.html`(参考源文件,含全部配色与布局;support.js 是旧运行时,**不要**引入,用原生 JS 重实现):

- 配色:页面底 `oklch(0.915 0.007 80)`,正文纸面 `oklch(0.998 0.002 85)`,边框 `oklch(0.82 0.01 80)`,AI 蓝系 `oklch(0.935 0.035 250)` / 文字 `oklch(0.22 0.05 250)`,高亮 `oklch(0.89 0.14 92)`,书签菱形 `oklch(0.62 0.13 60)`。
- 字体:`Noto Serif SC`(正文,行高 1.95,首行缩进 2em)/ `Noto Sans SC`(UI)/ `IBM Plex Mono`(编号、小标,letter-spacing .06–.14em)。
- 布局:52px header(书名+当前章节+层级切换+Search+Notes)/ 左侧 TOC(含 Scroll Spy 高亮、当前章子锚点、底部章节进度条)/ 中间正文(max-width ~720px 纸面)/ 46px footer(上一节 · `§x · Book y%` · 下一节,顶部 2px 全书进度线)。
- 三层:`Original`(纯原文)/ `Enhanced`(+边注、章导读、概念 hover)/ `Study`(+自测/知识路线全开)。切换按钮在 header,样式为分段控件。
- 必备交互(原生 JS,localStorage/IndexedDB 持久化到 `book:<id>:*`):
  - TOC 点击跳转 + Scroll Spy 反向高亮;⌘K/Ctrl+K 搜索(Exact 原文,区分 Concept 概念);
  - 选中文字弹浮条:Highlight / Note / Copy;Notes 抽屉(书签+高亮+笔记,可定位/删除);
  - 阅读位置恢复(关掉再开回到原处);字号调节可加在设置里(可省)。
- 概念 hover 卡:跟随鼠标,含名称/中英/一句话/First seen(跳转)/Related。

### 5. 输出

- 默认写到**桌面**:`Desktop/<书名> - <副题>.html`。
- 完成后渲染 PNG(如可用)交 visual-judge 验收:检查三层切换、TOC 高亮、边注不侵入正文、配色与参考一致。

## 注意

- 译文有版权:生成的 HTML 仅限用户本机个人使用,不要公开分发。
- PDF 输入时优先找同书 EPUB(Zotero 常两个都有);PDF 文本抽取用 pdftotext/PyMuPDF,注意繁简与分栏。
- 小说类(如《悉达多》)的蒸馏重点是**意象/人物/母题**概念卡与"这一部在讲什么"导读,不要写成剧情复述。
