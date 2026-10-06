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
0 摸底 → 1 研究 → 2 证据账本 → 3 概念图 → 4 教学架构 → 5 VISUAL STORYBOARD → 6 写稿 → 7 构建 → 8 验证 → 9 交付
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

页面格式:`## P07 · 标题 {mode=theater objects=source,system,response inherits=P02}` 开页。
模式:`theater`(大图+一句旁白)/`derive`(图+公式同步)/`read`(默认纸面)。
块:```scene```(逐拍 SVG:组内 `data-beat="N"` 分拍,`data-fx="grow|slide"` 变换,
旁白写 `<bN>一句话</bN>`,持久对象标 `data-obj="source|response|delta|kernel|system"`);
```predict```(Prediction→Reveal,先猜再看);```notes```(严谨层:方程/假设/证明细节,
默认折叠);```sources```;```quiz```;```capsule 标题```;```lab```(参数交互);
```callout 标题```;```visual```(静态 SVG)。

**Scene→Beat 铁律**:`→` 先推进当前页的拍,拍放尽才翻页。
一个 scene 只讲一个认知动作的分解,3–7 拍;旁白一句 ≤30 字。
持久对象跨页不换画法:source 橙、response 蓝、δ 金、kernel 深蓝、operator 灰
(registry 记在 dossier),位置语义固定:源在左/输入位,算符在中,响应在右。

**Storyboard 先行**:动笔前先填 dossier 的 Visual Storyboard 表
(Scene | Question | Persistent objects | Beat change | Formula born | Prediction),
先设计分镜再写正文,禁止"先写文章再找地方插图"。

写作纪律(全部来自 spec,逐条执行):

- **不以定义开场。** 第 1 页给 Hero Phenomenon(令人惊讶的具体现象 + 一个问题)。
- **Teaching Compiler 顺序**:WHY → CONCRETE PROBLEM → INTUITION → VISUAL MODEL →
  PATTERN → FORMAL DEFINITION → FORMULA → DERIVATION → WORKED EXAMPLE →
  GENERALIZATION → CONNECTION → APPLICATION → LIMITATION。
- **Formula Anatomy**:重要公式首现必拆——每个符号是什么/输入输出/量纲/正负号/
  变量与参数/假设/参数增大与极限行为。只给公式 = 不合格。
- **禁止数学瞬移**:不得出现"显然可得/经过简单计算/it is obvious/after some algebra"。
- **公式验证**:量纲、符号、极限、特例、数值 sanity,结果记入 dossier 验证日志。
- **Example Ladder** / **Generalization 三问** / **Connection Map** /
  **限制与失效** / **Science→Engineering→Industry 具体链条** / **Frontier 近三年**。
- 语言执行 ste-speech 的 clarity layer;Simple language ≠ simple science。
- 3B1B 五行为:**Persistence + Transformation + Prediction + Emergence + Minimalism**
  (详见 **references/visualization-policy.md**)。
  Theater/derive 页首屏正文 ≤120 中文字,严谨内容进 notes。

### 5. 构建

```bash
node "<skill>/scripts/lecture.mjs" build lecture.md -o out.html --dossier dossier.md
```

需要数学排版:`npm install katex` 一次(在 lecture.md 所在目录或 skill 目录)。
lecture.mjs 在构建期把 LaTeX 渲染成 HTML(服务端),产物零数学 JS、完全离线。
没有 katex 也能构建(数学降级为等宽块并告警)。
lint 拦截:数学瞬移用语、页码断档、无来源页;`--dossier` 再做证据审计
(claim 存在性、来源登记、used-in 双向核对、置信缓和词、孤儿);
视觉审计:核心链页必须有 scene/visual/lab,声明 objects 必须真实出现在 SVG,
inherits 必须延续对象,theater 首屏文字 ≤120 字。

### 6. 验证与交付

- headless 浏览器渲染 PNG(首/中/尾 + 暗色),交 visual-judge。
- 对照验收清单(**references/html-spec.md** 末节)逐项过。
- 默认输出:`Desktop/<主题>-lecture/<slug>.html`,dossier 与 lecture.md 同目录留档。

## V1 明确不做

TTS、MP4、Manim、3D/WebGL、语音、花哨转场。核心是研究、证据、逐页教学、数学、测验。
