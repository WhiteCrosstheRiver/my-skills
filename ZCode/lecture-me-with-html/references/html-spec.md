# HTML Spec — 逐页 Lecture 的骨架与验收

## 设计血统

配色与字体继承 book-distiller 阅读器(oklch 纸面 + 衬线正文 + mono 标号),
架构继承"52px header / 46px footer / 居中正文"的全屏框架,但**核心单位是 page**,
不是可滚动的长文——一屏一页,← → 翻页。

## 骨架(assets/lecture-template.html 已实现,勿重造)

```
header: 标题·副题 | 页码 07/21 | 目录 | 来源 | 明/暗 | 重学
main:   <section class="page"> × N,只显示当前页;页内 max-width 880px
footer: 进度条 | 上一页 | 页码 | 下一页
overlay: TOC(全页列表+当前高亮) / Sources(全源清单,按 tier 分组)
```

## 交互(V1 必备清单)

← → 翻页;Space 下一页;Home/End 首末页;数字键+Enter 跳页(可免);
TOC 点击跳页;每页底部显示该页 sources;quiz 点击判分;localStorage 记进度与模式;
暗/亮切换;重学(reset 清进度回第 1 页);响应式(窄屏 TOC 全屏、正文单列)。

## 数学

构建期 KaTeX 服务端渲染。`.katex` 继承正文颜色(暗色模式自动适配)。
display 公式块居中,可横向滚动不折断。

## 页面内容纪律

- 每页开头一句"这页在干什么"(可省,但页标题必须承担)。
- 页底部:来源 chips(该页 S 编号)。
- 图必须有 caption 回答"帮用户理解什么"。
- ```lab``` 块:canvas 交互,顶部一句"你在看什么",暂停/重置必备,
  参数 clamp,document.hidden 暂停,devicePixelRatio 适配。
  **翻页与 resize 后必须重新 fit+draw**:监听模板广播的 `lecturepage` 事件与 `resize`;
  只 `fit()` 不 `draw()` 会把画布清成空白(已踩过的坑)。draw 开头判 `W===0` 直接返回。

## 验收清单(交付前逐项过)

- [ ] ← → 可翻页,键盘不抢输入框焦点
- [ ] TOC / 来源 / 明暗 / 重学 四个按钮都工作
- [ ] 进度条与页码正确,刷新后回到原页
- [ ] 数学渲染正常(暗色模式下也正常)
- [ ] 图清晰有 caption;交互块极端参数不出 NaN
- [ ] 无 overflow、无 tofu;窄屏(≤800px)单列可读
- [ ] 不是 dashboard 堆卡片:每页一个认知任务
- [ ] 第一页不以定义开场
- [ ] 测验页覆盖 ≥4 种题型
- [ ] 渲染 PNG 交 visual-judge 通过
