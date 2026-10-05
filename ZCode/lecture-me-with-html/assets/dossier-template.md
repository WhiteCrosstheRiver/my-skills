# Research Dossier — <主题>

```yaml
topic: <中文名>(<英文名>)
date: YYYY-MM-DD
learner:
  math_level: <undergraduate-basic | …>
  physics_level: <…>
  domain_level: <…>
lecture_file: lecture.md
```

## 0. Learner 档案与教学立场

- 数学解释速度:……(依据 math_level)
- 领域例子深度:……(依据 domain_level)
- 已知卡点(来自 Tier E 或用户历史):……

## 1. Research Questions(检索记录)

| # | 问题 | 状态 | 命中来源 |
|---|---|---|---|
| Q1 | <概念> historical motivation | done | S1 |
| Q2 | intuitive explanation 最佳讲法 | done | S4,S7 |
| … |  |  |  |

## 2. Sources(按 tier)

### Tier A — 原始与权威
- **S1** [标题](URL) — 用途一句话
### Tier B — 大学教学资料
- **S3** […](…) — …
### Tier C — 优质直觉资源
- **S7** […](…) — …
### Tier D — 工程与产业
- **S9** […](…) — …
### Tier E — 社区讨论
- **S11** […](…) — 常见卡点

## 3. Concept Graph(决定页序)

```
<ASCII 概念图:节点=概念,边=依赖;标注主要对象的固定颜色>
```

- 对象配色:源=橙、响应=蓝、单位冲击=黄(示例;跨页保持)

## 4. Prerequisites(前置知识清单)

- 线性、叠加、矩阵逆、δ 函数、傅里叶……
- 每项标注:用户大概率已会 / 需要 capsule(capsule 编号 K1…)

## 5. Claim Ledger(唯一事实源)

| ID | Claim | Type | 来源 | 置信 | 假设 | 用于 |
|---|---|---|---|---|---|---|
| C001 | … | definition | S1,S3 | high | … | P05 |

## 6. Formula Verification Log

| ID | 对象 | 验证项与方法 | 结果 |
|---|---|---|---|
| V-01 | <公式> | 量纲/符号/极限/特例/数值(工具:node|python) | 通过 |

## 7. Open Questions(没查到/存疑,页面必须回避或明示)

- …
