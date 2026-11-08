# Book Distiller — 书籍 → 蒸馏阅读 HTML

把一本"线性文件"(EPUB/PDF)重新编译成一个**可阅读、可导航、可检索、可蒸馏、可回溯的知识对象**(Structured Distilled Book)。

> 核心原则:**原文是主干,蒸馏是增强层**;**没读过的段落不写边注**(每条边注带原文 quote,校验器核对)。

## 产物形态

每本书一个独立 HTML(或 HTML + `assets/<书名>/img/` 图片目录):

- **三层阅读模式**:Original(纯原文)/ Enhanced(章导读+边注+概念卡)/ Study(+自测)
- **章导读卡**:这一章要回答什么 / 知识路线 / 关键点(可跳到原文段落)/ 补充 / 阅读时长
- **AI 边注**:钉在具体段落,同一段可多条;Deeper 展开
- **概念卡**:正文虚线词 hover(名称/英文/一句话/首次出现跳转/相关概念)
- **自测题**:每章可多题
- **阅读器**:目录 + 小节标题导航 + Scroll Spy、Ctrl+K 双模式搜索、选中 Highlight/Note/Copy(刷新后高亮仍在)、Notes 抽屉、书签、进度与位置恢复;存储不可用时(沙箱/隐私模式)照常显示
- **原书插图**:按"第 k 段之后"锚点插回;≤2MB 内联,更大外挂 assets

## 流水线(v2)

```
Zotero 书 / EPUB / PDF ─→ bookir.py ─→ Book IR (ir/book.json + ir/img/ + quality 报告)
                       ─→ read_ir.py 逐章通读 ─→ parts/ch-NNN.json(每章一个,断点续跑)
                       ─→ check_distill.py merge ─→ distill.json(校验 0 error)
                       ─→ build_book.py ─→ <书名>.html (+assets/)
```

| 文件 | 作用 |
|---|---|
| `SKILL.md` | skill 定义(流程、蒸馏规范、校验与验收) |
| `book-distiller/bookir.py` | **v2 抽取器**:EPUB 用真正的 HTML 解析(嵌套 div 不再并成一段、保留 `<br>` 与短章、NCX/nav 多级目录与 `#锚点` 切章、ruby 去注音)、PDF 按块重建段落(去页眉页脚页码、去连字符、跨页续段、按目录标题而非整页切章、扫描件诚实失败)、图片随段锚定;直接读本机 Zotero(只读快照,EPUB 优先);输出质量报告 |
| `book-distiller/read_ir.py` | 整章带 `[章.段]` 编号分页阅读、全书精确查找(替代只看章首两句的 `sample.py`) |
| `book-distiller/check_distill.py` | 合并逐章 part + 校验:下标、quote 必须是所钉段落的原文、概念名必须是原文子串、`first` 自动修正、覆盖度警告 |
| `book-distiller/build_book.py` | 渲染器;构建前自动校验 |
| `book-distiller/tests/` | 合成 EPUB/PDF 的端到端测试(`python -m pytest book-distiller/tests`) |
| `extract_batch.py` / `extract_images_v2.py` / `backfill_images.py` | v1 管线(整库批量时代);已有 v1 IR 与蒸馏稿仍可用 `build_book.py --legacy` 渲染 |
| `build_siddhartha.py` / `distill_siddhartha.py` | 悉达多单书示例 |
| `IMAGE_ANALYSIS.md` | v1 图片管线设计报告 |

### distill.json schema

```json
{
 "subtitle": "作者/副题",
 "entry":  {"<章>": {"q":"这一章要回答什么","route":["关键词链"],"keys":[{"text":"关键点","at":段}, "关键点"],"motif":"补充","time":分钟}},
 "notes":  {"<章>": [{"at":段,"tag":"KEY","text":"一句话提炼","deeper":"可选","quote":"该段原文逐字片段"}]},
 "quiz":   {"<章>": [{"q":"问题","a":["A","B"],"correct":0,"fb":"解析"}]},
 "concepts":[{"id":"ascii-id","name":"原文逐字子串","en":"","one":"一句话","first":[章,段],"rel":["相关概念"]}]
}
```

v1 的边注列表 `[段, "TAG", "提炼", "Deeper"]` 仍可读;没有 quote 的旧稿需 `--legacy`。

## 使用(单本书)

```bash
python book-distiller/bookir.py zotero-list --query 书名
python book-distiller/bookir.py zotero-extract <ITEM_KEY> work/ir     # 或: bookir.py extract book.epub work/ir
python book-distiller/read_ir.py outline work/ir
python book-distiller/read_ir.py chapter work/ir 0                     # 读完一章 → 写 work/parts/ch-000.json
python book-distiller/check_distill.py merge work/ir work/parts work/distill.json
python book-distiller/build_book.py work/ir work/distill.json "<书名>.html" "<书名>"
```

## 整库批量经验(v1,526 本实测)

- v1 管线曾完成 526 本书的整库批量(524 成功 / 2 本源文件损坏诚实失败)。v2 的主要改进针对 v1 暴露的问题:段落结构丢失、短章/诗行丢失、PDF 页眉页码混入、蒸馏只看章首导致边注空泛。
- **断点续跑**:v2 以 `parts/ch-NNN.json` 为粒度;模型线程掉线最多损失一章。
- **调度**:免费档线程易被并发上限锁定,**同一时间只跑一个蒸馏线程**,掉线后从缺失的 part 续跑,不并发重试。
- **诚实失败**:OCR 全乱码、正文是广告、IR 只剩目录的书一律记录原因并跳过,**绝不编造正文**;合集书名与实际内容不符时按实际内容蒸馏并注明。

## 版权说明

生成的 HTML 含书籍全文(版权属出版社/译者),**仅限本机个人使用,请勿公开分发**。本仓库只收录管线代码与文档,不包含任何 Book IR 正文、蒸馏产物或书籍数据。
