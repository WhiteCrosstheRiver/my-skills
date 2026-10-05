# 交互讲解 HTML 设计规格(concept-lab 第 3 层)

**起点是 `assets/template.html`,不是空白文件。** 复制它,改内容,加交互。
模板的 CSS token 逐条取自 book-distiller 渲染器(`books/book-distiller/build_book.py`)的
真实样式,不是"凭印象的近似"。本文件讲结构语义和验收标准。

## 骨架 = book-distiller 阅读器(全屏应用框架,不是居中卡片页)

```
#frame  grid: 52px header / 1fr main / 46px footer
header  衬线书名(.t1)+ 副题(.t2)+ 三层分段控件(.seg)+ Search 按钮(kbd 芯片)
main    220px 左 TOC 轨(Scroll Spy 高亮 + 底部进度条)+ 760px 纸面 article
footer  左 §节号 / 中 书名 / 右 百分比;顶部 2px 深色进度线随滚动增长
```

- article:760px,17.5px 衬线,行高 1.95,padding 56px 64px,纸面 `oklch(0.998 0.002 85)`。
- AI 内容一律淡蓝卡:`.entry` 导读卡(路线 pills + 开始阅读按钮)、`.mnote` 边注
  (mono 小标 `AI · KEY / SECTION DISTILLED / COMMON PITFALL / CONNECTION` +
  "Why? 为什么"展开)、`.quiz` 自测卡(按钮判分:正确变绿、错误变红亮出正确项)。
- **三层语义(必须实现,验收员按此判)**:
  - Original:只有正文。导读卡、边注、误区、自测全部隐藏。
  - Enhanced:+ 导读卡、边注、术语点线下划线、误区卡。**自测仍然隐藏**。
  - Study:+ 自测(3 道,至少 1 道要回实验区操作才能答)。
  - TOC 条目跟随所属层隐藏(自测条目只在 Study 出现——这是对的,不是 bug)。
- 实验区 `.lab`(深底 `oklch(0.22 0.02 250)`):canvas 上格模拟/下格曲线,控件在下,
  每个控件人话标签 + mono 当前值,"你在看什么"一行,暂停/重置必备。
  深底与纸面的明暗对比 = 原书/AI 之外的第三个区:"实验室"。读者永远知道自己在哪层。

## 工程要求(每条都来自真实故障模式)

- 数值控件:读值后 `clamp` 到合法区间再参与计算。除法先判零。ζ/速度类状态量加 clamp。
- 动画用 `requestAnimationFrame`。`document.hidden` 时暂停。
- canvas 按 `devicePixelRatio` 缩放(模板 `hidpi()`)。`resize` 后重新 fit。
- 三层切换用 JS 给 `[data-layer]` 加 `.hidden{display:none!important}`,
  不要用 `display:revert`——它会把 `.entry` 的 grid 打回 block(TDZ/布局双重坑)。
- 脚本初始化调用放在所有定义之后(模板内 `setMode` 依赖 `spy`/`scroller`)。

## 自查清单(渲染 PNG 给 visual-judge 前先自己过)

- [ ] 打开即懂:题头一句话不依赖上下文
- [ ] 每个滑块从最小拖到最大:曲线/模拟连续变化,无跳变,无 NaN
- [ ] 三层切换:Original 干净、Enhanced 有导读+边注、Study 才见自测;TOC 同步
- [ ] 误区卡与自测题存在;quiz 点错亮红并亮出正确项
- [ ] 控件标签说人话:写 ε(LJ 深度),不写 epsilon
- [ ] 断网打开无外部请求(grep `http` 应无 CDN 引用)

## 工程要求(每条都来自真实故障模式)

- 数值控件:读值后 `clamp` 到合法区间再参与计算。除法先判零。
  理由:用户一定会在极值处拖。数字变 NaN/Infinity,页面就废了。
- 动画用 `requestAnimationFrame`。`document.hidden` 时暂停。
  理由:切标签页后不暂停,回来时模拟状态已飞掉。
- 高 DPI:canvas 按 `devicePixelRatio` 缩放(模板的 `hidpi()` 已做)。
  不做,Retina 屏上文字发虚。
- 响应式:正文 max-width ~720px。窄屏(≤800px)控件纵向堆叠(模板已做)。
- `window.resize` 后重绘 canvas。不做,拖窗口后画布空白或错位。

## 自查清单(渲染 PNG 给 visual-judge 前先自己过)

- [ ] 打开即懂:题头一句话不依赖上下文
- [ ] 每个滑块从最小拖到最大:曲线/模拟连续变化,无跳变,无 NaN
- [ ] 误区卡与自测题存在。解析在 details 内
- [ ] 控件标签说人话:写 ε(LJ 深度),不写 epsilon
- [ ] 断网打开无外部请求(DevTools Network 面板验证,或 grep `http`)
