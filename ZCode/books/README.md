# Book Distiller — 书籍 → 蒸馏阅读 HTML

把一本"线性文件"(EPUB/PDF)重新编译成一个**可阅读、可导航、可检索、可蒸馏、可回溯的知识对象**(Structured Distilled Book)。

> 核心原则:**原文是主干,蒸馏是增强层**。任何 AI 内容不得打断原书阅读,不得让读者失去"我在原书哪里"的感觉。原文与 AI 内容视觉隔离(白底=原书,淡蓝 AI 卡片,全部带 `AI ·` 小标)。

本 skill 已在 ZCode 中实测完成 **526 本书的整库批量蒸馏(524 成功 / 2 本源文件损坏诚实失败)**,产物 574MB(525 个 HTML + 200 个图片 assets 目录)。

## 产物形态

每本书一个独立 HTML(或 HTML + `assets/<书名>/img/` 图片目录),包含:

- **三层阅读模式**:Original(纯原文)/ Enhanced(章导读+边注+概念卡)/ Study(自测题)
- **章导读卡**:这一章要回答什么 / 知识路线链 / 关键点 / 母题 / 预计阅读时长
- **AI 边注**:锚定到具体段落的 KEY / REASONING / COMMON PITFALL / CONNECTION / 母题笔记,可展开 Deeper
- **概念卡(Concept Registry)**:正文中虚线词 hover 弹出(名称/英文名/一句话/首次出现跳转/相关概念)
- **自测题(Quiz)**:Study 模式下按章出题+解析
- **阅读器功能**:左侧目录 + Scroll Spy 反向高亮、Ctrl+K 双模式搜索(Exact 原文 / Concept 概念)、选中文字 Highlight/Note/Copy、Notes 抽屉、书签、阅读进度与位置恢复(localStorage)
- **原书插图**:按"第 k 段之后"锚点插回正文;≤2MB 图片 base64 内联保持单文件,大书自动外挂 assets 目录

## 流水线

```
EPUB/PDF ─→ extract_batch.py ─→ Book IR (batch/ir/<idx>/book.json)
         ─→ extract_images_v2.py ─→ 图片旁挂(零位移)
         ─→ [AI 蒸馏] batch/distill/<idx>.json (entry/notes/quiz/concepts)
         ─→ build_book.py ─→ <书名>.html (+assets/)
backfill_images.py = 已建书补图重建(幂等)
```

### 文件说明

| 文件 | 作用 |
|---|---|
| `SKILL.md` | skill 定义(核心原则/流水线/蒸馏规范/渲染规范) |
| `extract_batch.py` | 批量扫描书库 → 选最佳格式(EPUB>PDF)→ 抽取文本成 Book IR;幂等,已有输出自动跳过 |
| `extract_images_v2.py` | 图片旁挂抽取:EPUB 按 `<img>` 字节偏移锚定,PDF 按 `get_text("dict")` 块 y 序锚定;**paras 逐字节零位移**(蒸馏稿全复用);过滤 <10KB/短边<100px/重复>3 次装饰图,>4MB PIL 压缩 |
| `build_book.py` | 通用渲染器:读 book.json + distill.json → 单文件 HTML(oklch 暖调/Noto Serif/三层模式/搜索/笔记/图片混合交付) |
| `build_siddhartha.py` | 单书一体构建器(悉达多示例,数据内联) |
| `distill_siddhartha.py` | 悉达多蒸馏数据示例(章导读/边注/概念卡/自测的完整写法) |
| `backfill_images.py` | 对已建 HTML 的书回填图片并重建(阶段1 已建书/阶段2 未建书只升 IR) |
| `sample.py` | IR 采样器(蒸馏前抽读章节首中尾段,不整章 dump) |
| `IMAGE_ANALYSIS.md` | 图片管线完整设计与原型验证报告 |

### 蒸馏数据 schema(distill.json)

```json
{
 "subtitle": "作者/副题(简短)",
 "entry":  {"<章下标0based>": {"q":"这一章要回答什么","route":["5-8关键词路线链"],
            "keys":["2-4条关键点"],"motif":"补充一句话","time":分钟}},
 "notes":  {"<章下标>": [[段下标0based,"TAG","一句话提炼",(可选"Deeper展开")]]},
 "quiz":   {"<章下标>": {"q":"问题","a":["A","B","C"],"correct":0,"fb":"解析"}},
 "concepts":[{"id":"ascii-id","name":"必须为原文完整子串","en":"","one":"一句话",
              "first":[章下标,段下标],"rel":["相关概念"]}]
}
```

硬性预算:entry ≤ min(章数,15);notes 全书 ≤20 且段落下标真实;quiz ≤4;concepts 8~15 且 `name` 必须是原文完整子串(hover 才会触发)。小说蒸馏母题/人物/意象/结构(不复述剧情);非虚构蒸馏核心论点/方法/可行动建议;全部中文,不得编造引文。

## 使用(单本书)

```bash
python extract_batch.py <书库目录> <输出根目录>     # 批量抽取 IR
python extract_images_v2.py --apply batch/ir/<idx>  # 补图片(可选)
# 写 batch/distill/<idx>.json(手工或 AI)
python build_book.py batch/ir/<idx> batch/distill/<idx>.json "<书名>.html" "<标题>"
```

## 整库批量经验(526 本实测)

- **断点续跑**:一切以 `batch/status/<idx>.json` 为准,重跑自动跳过已完成;agent 被杀最多损失一本书的部分进度。
- **多智能体调度**:账号并发上限约 10 且被其他会话波动抢占——"渗透式补位"(每个完成/失败通知补 1-2 个,被拒零成本下轮再试,绝不单轮连发 3+);收尾用 **sweep 式 agent**(每轮自己扫缺失、处理 8 本、报告余量),按低/中/高段分工避免竞写,撞车方验证已有 distill 而非覆盖。
- **额度**:全程免费档 GLM-5.3-Flash,每包 6 本约 100万-500万 tokens,1 亿/日额度跨 3 天跑完;设置页余额是快照需手动刷新。
- **诚实失败**:OCR 全乱码(0% 中文)、正文是广告、IR 只剩目录的书,一律 `ok:false` + 原因,**绝不编造正文**;合集书名与 IR 实际内容不符时按实际内容蒸馏并注明。

## 版权说明

生成的 HTML 含书籍全文(译文版权属出版社/译者),**仅限本机个人使用,请勿公开分发**。因此本仓库只收录管线代码与文档,不包含任何 Book IR 正文、蒸馏产物 HTML 或书籍数据。
