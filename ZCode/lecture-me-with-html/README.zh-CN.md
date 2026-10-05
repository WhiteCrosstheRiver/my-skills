# lecture-me-with-html

重型教学器:把一个概念做成一本可翻页、可推导、可自测的单文件 HTML Lecture。

> Answer Me(轻)让你快速看懂一个答案;Lecture Me(重)让你真正学会一个概念。

## 流水线

```
Topic → Deep Research(按问题搜索)→ Evidence/Claim Ledger → Concept Graph
→ Teaching Architecture → 逐页写稿 → lecture.mjs 构建 → 公式验证 → 翻页 HTML
```

## 使用

1. 对 agent 说:"用 lecture-me-with-html 讲透 格林函数"。
2. agent 会先多源研究,产出 `dossier.md`(来源金字塔 + claim 账本),
   再逐页写 `lecture.md`,最后构建出 HTML。
3. 构建:`node scripts/lecture.mjs build lecture.md -o greens-function.html`。
   数学排版需一次性 `npm install katex`(构建期渲染,产物完全离线、零数学 JS)。

## 产物形态

一页一认知任务,← → 翻页;公式 LaTeX 真排版;每页带来源;结尾五种题型测验;
明/暗模式;进度记忆;重学按钮。

## 目录

```
SKILL.md                    流水线与写作纪律
references/                 研究/来源/证据/教学/数学/可视化/产业/测验/HTML 九项政策
assets/lecture-template.html  翻页 Lecture 骨架(含全部 CSS/JS)
assets/dossier-template.md    研究档案 + Claim 账本模板
scripts/lecture.mjs         构建器:解析/KaTeX/lint/组装
examples/greens-function/   dogfood 样例(dossier + lecture 源 + 成品)
```

## 血统

设计 tokens 继承本仓库 `books`(book-distiller 阅读器)的纸面美学;
教学动作借鉴 3Blue1Brown(progressive reveal / visual continuity / formula emergence);
与 `answer-me-with-html` 共享 STE 清晰性原则,但架构独立、零 sibling 依赖。
