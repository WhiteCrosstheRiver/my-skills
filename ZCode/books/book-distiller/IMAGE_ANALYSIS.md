# 图片丢失分析与原型验证报告

日期:2026-09-28。本文档回答一个问题:**当前管线(extract_batch.py → build_book.py)丢掉了原书的全部图片,损失有多大、能否低成本补回来、怎么补。**

结论先行:
- **损失是全局性的**:526 本已入库图书中 **525 本**的源文件含图片(仅 1 本无图),而生成 HTML 中 `<img>` 数量为 **0**。
- **EPUB 补图完全可行**(原型已跑通:366/366 图片全部解析成功、路径映射零失败)。
- **PDF 补图可行**(pymupdf `get_text("dict")` 的 type=1 图像块天然按阅读顺序排列,可直接交错插回)。
- **推荐方案**:paras 文本列表保持不变(保护 111 份 distill JSON 的段落索引),图片作为**独立锚定列表** `"images"` 旁挂;交付采用**混合模式**——图片总量 ≤2MB 的书内联 base64 保持单文件,大图书用 `assets/<slug>/` 相对路径目录。

---

## 一、损失量化

### 1.1 样本对照表(源文件 vs 生成 HTML)

| 书 | 源格式 | 图片数 | 图片体积 | >10KB 图 | HTML 中 `<img>` |
|---|---|---:|---:|---:|---:|
| 一天一朵云+云彩收集者手册 | .epub | 359 | 13.4 MB | 319 | **0** |
| 人间小满 姑苏阿焦(同 人间小满1) | .epub | 248 | 19.1 MB | 247 | **0** |
| 世界咖啡地图 (James Hoffmann) | .epub | 366 | 28.2 MB | 259 | **0** |
| 1984(中英双版) | .epub | 1 | 0.44 MB | 1 | **0** |
| 三体全集 | .epub(选中)/另有 .pdf | 33 | 19.3 MB | 5 | **0** |
| 一见你就好心情+你今天真好看 (莉兹·克里莫) | .epub | 161 | 9.7 MB | 161 | **0**(该书 extract_fail,连文字都没有) |

注:"一见你就好心情"是**纯漫画书**(161 张图几乎全是内容图,>10KB 占 100%),extract_fail 的原因正是全文段落数 <20 被判定失败——图恰恰是这本书的全部内容。

### 1.2 全库扫描(manifest 全部 612 条,EPUB 用 zip 清单精确统计字节;PDF 用 get_images 统计去重 xref)

- 扫描成功 609 本(567 epub + 42 pdf),0 错误。
- **含图片的书:608/609**;图片 >1MB 的书:338 本。
- **ir_ready 的 526 本中:525 本含图**。EPUB 513 本,图片合计 **2.8 GB**,中位数 **1.22 MB/本**,均值 5.53 MB/本;>2MB 的 201 本,>10MB 的 68 本。PDF 13 本(ir_ready),粗估 5.3 GB(按像素×1.2 估算,偏高,仅作量级参考)。
- 图片最重的书:228可怕的两岁(PDF,440 图)、以利为利(epub,527 图 158MB)、柏杨白话版资治通鉴(epub,2057 图 137MB)、这里是中国(epub,441 图 87MB)等。

### 1.3 现状代码丢图位置

- `extract_epub` → `epub_paras()`:`re.sub(r"<[^>]+>", "", ...)` 把所有标签剥掉,`<img>`(含 SVG `<image>`)就地蒸发,且无任何记录。
- `extract_pdf`:`p.get_text("text")` 只取文本流,图像对象完全不进入 IR。
- `build_book.py`:`chapters[].paras` 只有字符串,渲染端没有插图的任何通路。

---

## 二、EPUB 图片提取原型(已跑通,脚本:`batch/_imgtest/epub_proto.py`)

样本:世界咖啡地图.epub(366 图,28.2 MB)。要点与结果:

1. **路径解析规则**:OPF manifest 给出 id→href(相对 OPF 目录),spine 给出阅读顺序的 XHTML。XHTML 内 `<img src>` / SVG `<image xlink:href>` 需**相对该 XHTML 所在目录**解析:`posixpath.normpath(posixpath.join(dirname(doc), unescape(src)))`。本书全部为同目录形式(`src="main-1.jpg"`);实际书目中还有 `../Images/xx.jpg`(上跳一层)与 `OEBPS/` 子目录等形式,统一用 posixpath.normpath 即可覆盖,`#fragment` 要先 split 掉。
2. **解析成功率:366/366 = 100%**,0 个未解析目标、0 个"引用了但 zip 里不存在"、0 个引用了但不在 manifest 的图。zip 中也**没有**未被正文引用的孤儿图(本书如此;其他书可能有 cover 页,按"未被引用→并入章尾/作书封"兜底)。
3. **字节与尺寸**:PIL 可用,读字节流得 w×h;退化方案是解析 PNG/JPEG 头(原型里也实现了)。分类(按体量):cover 1 张 0.2MB;**内容图 268 张 26.0MB**;装饰性小图(<15KB 或 <120px)97 张共 0.65MB —— 装饰图只占 2.5% 的字节,可安全跳过。
4. **提取落地**:366 张图已写入 `batch/_imgtest/extract_coffee/`(28MB),文件名 = zip 内路径扁平化。
5. 锚定方式:按 spine 文档顺序遍历 body,`re.finditer` 匹配 `<img>` 的**字节偏移位置**,数一下该位置之前已产出的段落数,即得"插在第 k 段之后"的锚点——与 `epub_paras()` 的遍历顺序完全同源,锚点稳定。

---

## 三、PDF 图片在位提取原型(已跑通,脚本:`batch/_imgtest/pdf_proto2.py`)

样本:一天一朵云.pdf(454 页,每页一图一注的摄影书);对照:三体.pdf(1302 页文字书)。

1. **阅读顺序天然可用**:`page.get_text("dict")` 返回 blocks,`type=0` 文本、`type=1` 图像,按版面 y 序排列。实测第 16 页流程:T('如果你不知道读什么书…')→T→T→**I(860×860 jpeg 100KB)**→T('微信公众号名称…')→T——图像块出现在它版面上的真实位置,插回"第 k 段之后"只需按 block 顺序累计文本块即可。
2. **两种取字节方式**:本机 pymupdf 1.28.2 的 dict 图像块自带 `image`(bytes)、`ext`、`width`、`height`、`mask` 键,可直接落盘;或按页 `page.get_images(full=True)` 拿 xref,再 `doc.extract_image(xref)`(两种都验证过,输出一致)。dict 方式不需要 xref,更简单且天然带位置。
3. **实测提取**:`p18_x627_430x430.jpeg`(39KB)等已写入 `batch/_imgtest/extract_cloud/`。
4. **体量分布与阈值**:一天一朵云 362 张去重图,中位 114KB,无小装饰图(整本书都是内容图)。三体.pdf 仅 7 张:2 张封面(1.25MB)、1 张 7.4MB 大图、**1 张 72×72 2KB 的装饰 png**。建议阈值:**短边 <100px 或体积 <10KB 跳过**(装饰性页眉/花线),同时设单图上限(如 >4MB 时缩存/降质)防个例爆体积。
5. 注意点:PDF 的"章节"由 toc 页码切分,段落由页文本拼出;图像锚点 = 所在页 + 该页内前置文本块数,映射到该章已生成段落序列,同样不影响文本索引。

---

## 四、设计建议

### 4.1 IR schema:推荐「paras 不动 + 旁挂 anchored images 列表」

```json
{
  "chapters": [
    {"title": "...", "paras": ["原文段落…", "..."],          // ← 完全不变
     "images": [ {"after": 3,  "src": "img/p012-3.jpg", "w": 860, "h": 860},
                  {"after": -1, "src": "img/cover.jpg"} ]}      // after=-1 = 章首插图
  ],
  "images_dir": "assets/<slug>"                                  // build 时解析基准
}
```

理由(对比 `{"t":"img"}` 混入 paras 的方案):
- **distill JSON 全部免改**:111 份 distill 的 `notes[[paraIdx,…]]`、`concepts.first[ch,para]`、quiz 均按段落索引锚定,paras 一旦混入 img 项,后面所有段索引平移,111 份蒸馏稿全部作废——这是不可接受的。旁挂列表则**索引零位移**,旧蒸馏稿天然兼容。
- 提取端可独立回归验证:重跑后 `paras` 必须与 v1 逐字节一致(可用 diff 脚本校验),再叠加 images。
- 渲染端改动极小:`render()` 里在 `for i…paraEl()` 循环中查 `imgByAfter[i]` 即可,原文层(Original)也可选择隐藏图片保持纯文字。

### 4.2 交付:混合阈值(≤2MB 内联 base64,>2MB 走 assets/ 目录)

| 方案 | 优点 | 缺点 | 实测量级 |
|---|---|---|---|
| 全部 base64 内联 | 保持单文件,可单个拷走/同步 | HTML 体积爆炸;bookdata JSON 解析变慢 | 中位数 1.22MB→HTML +1.6MB 尚可;世界咖啡地图 28MB→**+37MB**;最重书 137MB→**+180MB**,双击打开都卡 |
| 全部 assets/ 目录 | HTML 恒定小 | 526 本书都有附属目录,"单文件"特性消失;移动单个 HTML 会丢图 | 图像总量 ~3GB(EPUB 实测) |
| **混合(推荐)** | 1984(0.44MB)、三体(33图)这类小图书仍单文件;摄影/漫画类大图书才带目录 | 两种形态并存 | 阈值 2MB 时约 325 本单文件、~200 本带 assets |

- `file://` 相对路径没有问题:`<img src="assets/世界咖啡地图/img/x.jpg">` 从 Desktop 目录的双击打开是允许的(file:// 页面引用同盘相对路径图片不受 CORS 限制,受限的是 fetch/XHR)。中文/空格路径浏览器会自动百分号编码,原型已验证 zip 路径扁平化命名(`main-1.jpg`)可进一步规避特殊字符。
- 内联时 base64 放在 **bookdata JSON 外**的独立 `<script type="application/octet-stream" id="imgdata">` 或直接生成 `img/{n}.data:image` 映射,避免把几 MB base64 塞进主 JSON 拖慢解析。

### 4.3 回填计划

受影响代码(共 4 处,均为增量,**不改文本抽取逻辑**):
1. `extract_batch.py / extract_epub`:加 `epub_images(z, doc)` —— 遍历 spine 文档的 `<img>/<image>`,算锚点、解析 zip 路径、按阈值过滤,写入 `ir/<idx>/img/` 与 book.json 的 `images` 字段(+80 行)。
2. `extract_batch.py / extract_pdf`:改用 `get_text("dict")` 取 block 流,文本块拼回与现状一致的 paragraphs(必须逐字节对齐 v1),图像块按阈值过滤、按"所在章 + 前置文本块数"锚定(+60 行)。
3. `build_book.py`:main() 透传 `images`,渲染器加 `<figure class="img">` 插入与一条 CSS;内联时生成独立 imgdata script(+25 行)。
4. 新增回填脚本:只对**源文件含图**的书重抽 v2 IR(525/526 本,全库扫描脚本已给出清单),重跑 build;**distill JSON 全部保留复用**,不需要重蒸馏(这是选旁挂 schema 的核心收益)。

顺序与校验:先写 paras 一致性 diff 脚本 → 重抽 IR → 校验 0 位移 → 重 build HTML → 抽查 3 本(世界咖啡地图/人间小满/一天一朵云)目检图片位置。工作量估计:**1 个开发日**(含回填运行与抽查);纯文字书(如 1984)不受影响。

附:原型产物位置
- `batch/_imgtest/quantify.py`(样本量化)、`broad_scan.py` + `broad_scan.jsonl`(全库清单)
- `batch/_imgtest/epub_proto.py` → `extract_coffee/`(366 张,28MB)
- `batch/_imgtest/pdf_proto.py` / `pdf_proto2.py` → `extract_cloud/`
