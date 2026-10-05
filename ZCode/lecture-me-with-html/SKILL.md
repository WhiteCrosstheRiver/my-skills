---
name: lecture-me-with-html
description: 重型教学器:把一个概念做成一本可翻页、可推导、可自测的单文件 HTML Lecture 小教材。先多源研究(Research First),再逐页教学(motivation → 直觉 → 公式 → 推导 → 例题 → 推广 → 产业 → 前沿 → 测验)。当用户说"我想真正学会 X / 讲透 X / 做一个 lecture / 系统教学 X / lecture-me-with-html"时使用。轻量快速解释用 answer-me-with-html;本 skill 用于真正的学习工程。
---

# Lecture Me with HTML — 重型教学器

> Answer Me 让用户快速看懂一个答案。Lecture Me 让用户真正学会一个概念。

交付物:**单文件 self-contained HTML Lecture**,一页一页翻(← →),每页只教一件事,
数学用 LaTeX 真排版,每个重要结论可追溯到来源,结尾有真测验。
不是 dashboard,不是长文章换皮。

## 与兄弟 skill 的分工(不要越界)

- `answer-me-with-html`:轻型解释器。一个问题一页纸。**不要修改它。**
- `concept-lab`:单个交互模拟页(原型参考)。
- 本 skill:完整学习工程。核心单位是 **lecture page**,不是 panel。

## 流水线(必须按顺序,不许跳步)

```
0 摸底 → 1 研究 → 2 证据账本 → 3 概念图 → 4 教学架构 → 5 写稿 → 6 构建 → 7 验证 → 8 交付
```

### 0. 摸底(不单独开轮次)

从上下文推断三档水平,写进 lecture.md 的 frontmatter:

```yaml
learner:
  math_level: undergraduate-basic      # 数学走多慢
  physics_level: undergraduate-basic   # 物理走多慢
  domain_level: semiconductor-research # 例子可以走多深
```

允许"数学慢讲、领域深讲"的错位——这正是个性化教学的价值。
推断不出才问,能推断就不问。

### 1. 研究(Research First,不可跳过)

**Do not answer first. Research first.** 不许只凭记忆开写。
用一切可用的检索工具执行 **按问题搜索**,不是只搜概念名。
研究问题模板与来源分级见 **references/research-policy.md** 和 **references/source-policy.md**。
产出写到 `Desktop/<主题>-lecture/dossier.md`(模板:assets/dossier-template.md)。

### 2. 证据账本(Claim Ledger)

每个进 Lecture 的重要结论,先在 dossier 里立 Claim:

```text
C017 | L G = δ(线性算符 + 指定边界条件) | definition
     | 来源 S3,S5,S9 | 置信 high | 假设:线性、边界齐次 | 用于 P07,P08
```

**Dossier 是唯一事实源。** HTML、图、例题、quiz 只能从 Claim 派生。
页面好看不构成新增未验证数据的理由。规则详见 **references/evidence-policy.md**。

### 3. 概念图 → 教学架构

先画概念图(节点 = 概念,边 = 依赖),再决定页序。
**教学顺序 ≠ 文献顺序。** 顺序服务于学习者,模板见 **references/pedagogy.md**。
前置知识可能缺失时,插入 Prerequisite Capsule(最小知识胶囊),不把用户赶走。

### 4. 写稿(lecture.md)

格式:`## P07 · 标题` 开页;`$$…$$` 数学;```sources``` 页面来源;
```quiz``` 测验;```capsule 标题``` 前置胶囊;```lab``` 交互模拟(原生 HTML/JS)。
写作纪律(全部来自 spec,逐条执行):

- **不以定义开场。** 先回答"这东西为什么被发明?没有它什么算不了?"
- **Teaching Compiler 顺序**:WHY → CONCRETE PROBLEM → INTUITION → VISUAL MODEL →
  PATTERN → FORMAL DEFINITION → FORMULA → DERIVATION → WORKED EXAMPLE →
  GENERALIZATION → CONNECTION → APPLICATION → LIMITATION。
- **Formula Anatomy**:重要公式首现必拆——每个符号是什么/输入输出/量纲/正负号/
  变量与参数/假设/参数增大与极限行为。只给公式 = 不合格。
- **禁止数学瞬移**:不得出现"显然可得/经过简单计算/it is obvious/after some algebra"。
  每步推导给出"为什么/用了什么假设/物理上意味着什么"。
- **公式验证**:量纲、符号、极限、特例、数值 sanity,结果记入 dossier 验证日志。
  用 python/node 算,不凭感觉。
- **Example Ladder**:toy → worked → scientific → engineering → industrial → research,
  按主题适配,不强凑六层。
- **Generalization**:每次抽象说明"什么变了/什么没变/核心结构是什么"。
- **Connection Map**:相邻概念(impulse response/matrix inverse/propagator/…)必须解释
  为什么相关,不许罗列名字。
- **限制与失效**:假设、失效条件、近似边界、常见误用,必须讲。
- **Science→Engineering→Industry**:给具体链条(理论→方法→软件→产品),
  禁止"广泛应用于工业"这类空话。
- **Frontier**:活跃主题检索近三年来源;经典结论与最新研究明确区分。
- 语言执行 ste-speech 的 clarity layer(一句一事、短句、术语稳定);
  Simple language ≠ simple science,专业词照用,但一个符号一个含义。
- 可视化按知识形状选型(见 **references/visualization-policy.md**),
  每张图必须回答"它帮用户理解什么",答不出就删。
- 交互只用于回答"参数变了会怎样",定义页不塞滑块。
- 3B1B 借鉴的是教学动作:progressive reveal、visual continuity、formula emergence、
  transformation 对应。不是模仿视觉风格。

### 5. 构建

```bash
node "<skill>/scripts/lecture.mjs" build lecture.md -o out.html
```

需要数学排版:`npm install katex` 一次(在 lecture.md 所在目录或 skill 目录)。
lecture.mjs 在构建期把 LaTeX 渲染成 HTML(服务端),产物零数学 JS、完全离线。
没有 katex 也能构建(数学降级为等宽块并告警)。
lint 会拦截:数学瞬移用语、页码断档、无来源页。规则见 **references/math-policy.md**。

### 6. 验证与交付

- headless 浏览器渲染 PNG(首/中/尾 + 暗色),交 visual-judge。
- 对照验收清单(**references/html-spec.md** 末节)逐项过。
- 默认输出:`Desktop/<主题>-lecture/<slug>.html`,dossier 与 lecture.md 同目录留档。

## V1 明确不做

TTS、MP4、Manim、3D/WebGL、语音、花哨转场。核心是研究、证据、逐页教学、数学、测验。
