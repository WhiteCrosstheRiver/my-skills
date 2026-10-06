---
title: 格林函数
subtitle: 从"敲一下"到量子器件——一个概念的全部旅程
date: 2026-10-05
learner:
  math_level: undergraduate-basic
  physics_level: undergraduate-basic
  domain_level: semiconductor-research
---
```bib
S1: [Cannell, George Green: Mathematician and Physicist 1793–1841](https://books.google.ba/books?id=x2Y2eb9IzwwC) — tier A — 1828 论文史实
S2: [MIT OCW 18.303 Linear PDE](https://ocw.mit.edu/courses/18-303-linear-partial-differential-equations-fall-2014/) — tier B — G=L⁻¹、LG=δ、边界条件
S3: [Strang, Delta functions and distributions (MIT)](https://math.mit.edu/~gs/) — tier A 论文 — δ 与脉冲响应
S4: [Datta, Nanoscale device modeling: the Green's function method (JPCM 2000)](https://courses.ece.ucsb.edu/ECE194/194A_S13Banerjee/References/Datta_NEGF.pdf) — tier A — NEGF 基础
S5: [Camsari et al., The NEGF Method (arXiv:2008.01275, 预印本)](https://arxiv.org/abs/2008.01275) — tier A 预印本 — NEGF 教学综述
S6: [QuantumATK NEGF Device 官方文档(Synopsys)](https://docs.quantumatk.com/manual/NEGFDevice.html) — tier D 官方文档 — 工业实现
S7: [Zhang et al., rNEGF, PRB 110, 155430 (2024)](https://journals.aps.org/prb/abstract/10.1103/PhysRevB.110.155430) — tier A — 大规模 NEGF,维度至 4×10⁵
S8: [Jin, Keer, Wang, IJSS 46(21):3788 (2009), DOI 10.1016/j.ijsolstr.2009.07.015](https://www.sciencedirect.com/science/article/pii/S0020768309002698) — tier A — 本征源应力 G
S9: [Pan & Chen, Static Green's Functions in Anisotropic Media (Cambridge UP 2015)](https://www.cambridge.org/9781107034801) — tier A 专著 — Kelvin/Mindlin
S10: [Physics SE: greens-functions 高赞问题](https://physics.stackexchange.com/questions/tagged/greens-functions?tab=Votes) — tier E — 误区与卡点
S11: [Strassler, Virtual particles: what are they?](https://profmattstrassler.com/articles-and-posts/virtual-particles-what-are-they/) — tier C — 传播子直觉
S12: [Krzeminski et al., J. Vac. Sci. Technol. B 30, 022203 (2012), DOI 10.1116/1.3683079](https://doi.org/10.1116/1.3683079) — tier D — 应力仿真 vs 实验
S13: [ASME: Introduction to FEM/BEM, BEM fundamentals](https://asmedigitalcollection.asme.org) — tier D — 基本解方法
S14: [Cao et al., Laplace Neural Operator, Nat. Mach. Intell. 6:631 (2024), DOI 10.1038/s42256-024-00844-4](https://www.nature.com/articles/s42256-024-00844-4) — tier A — Laplace 域神经算子
S15: [ML Green's Functions of Strongly Correlated Hubbard Models, J. Phys.: Condens. Matter (2025), DOI 10.1088/1361-648X/ae649b](https://iopscience.iop.org/article/10.1088/1361-648X/ae649b) — tier A — KRR 学自能
S17: [MIT OCW 18.03 Differential Equations](https://ocw.mit.edu/courses/18-03-differential-equations-spring-2010/) — tier B — 脉冲响应与卷积
S19: [Intel 官方背景材料:Strained Silicon](https://www.intel.com/pressroom/kits/advancedtech/doodle/ref_strain/strain.htm) — tier D 官方 — 90nm 应变硅量产
S20: [Green's Neural Operator with Neumann BC (OpenReview, 预印本)](https://openreview.net) — tier E 预印本 — 另一条神经算子线
```

## P01 · 先别看任何方程:敲一下,会发生什么? {mode=theater objects=source,response}

```scene
<b1>一根两端钉死的弦。先什么都不做。</b1>
<b2>在正中间,敲一下。(橙 = 源)</b2>
<b3>弦变成这个形状:中间鼓、两端不动。(蓝 = 响应)</b3>
<b4>记住这张图。整门课只研究它。</b4>
<svg viewBox="0 0 640 240" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <g data-beat="1">
    <rect x="26" y="120" width="14" height="60" fill="var(--ink3)"/>
    <rect x="600" y="120" width="14" height="60" fill="var(--ink3)"/>
    <line x1="40" y1="150" x2="600" y2="150" stroke="currentColor" stroke-width="2"/>
    <text x="60" y="200" fill="var(--ink3)" font-size="12">两端钉死</text>
  </g>
  <g data-beat="2" data-obj="source">
    <circle cx="320" cy="150" r="8" fill="oklch(0.68 0.15 55)"/>
    <path d="M 320 96 L 320 136" stroke="oklch(0.68 0.15 55)" stroke-width="3" marker-end="url(#arP1)"/>
    <defs><marker id="arP1" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="oklch(0.68 0.15 55)"/></marker></defs>
    <text x="338" y="112" fill="oklch(0.68 0.15 55)" font-size="12">敲一下(单位强度)</text>
  </g>
  <g data-beat="3" data-obj="response" data-fx="grow">
    <path d="M 40 150 L 320 70 L 600 150 Z" fill="oklch(0.72 0.12 250 / .18)" stroke="oklch(0.72 0.12 250)" stroke-width="2.5"/>
    <text x="330" y="62" fill="oklch(0.55 0.13 250)" font-size="12">响应(蓝)</text>
  </g>
  <g data-beat="4">
    <rect x="470" y="30" width="150" height="40" rx="8" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
    <text x="545" y="56" text-anchor="middle" fill="currentColor" font-size="13">=?任意载荷能预测吗</text>
  </g>
</svg>
```

```predict
如果只精确知道"每个位置敲一下后的响应",任意形状的重物压上去,能预测弦的形状吗?
- 不能,重物形状有无数种,得逐个重解
- [x] 能:任意载荷 = 无数个小敲击之和,响应直接相加
- 只能预测对称的载荷
?? 先带着猜往下走。P04 会证明"能",P09 会真的算一遍。猜错也没关系——猜过才记得住。
```

> 历史注脚:George Green 1828 年私人印发《论数学分析在电与磁理论中的应用》,
> "单位源响应"的思想就在里面;当时只卖出约 50 份,靠 Kelvin 推动才广为人知。[C020]

```sources
S1 S2
```

## P02 · 最简单的问题:两个弹簧 {mode=theater objects=system,source}

```scene
<b1>把弦简化到只剩两个自由度:两个弹簧块。</b1>
<b2>平衡方程:矩阵形式 A·x = b。A 的每个元素 = 一根弹簧。</b2>
<b3>b 是外力(橙),x 是位移(蓝)。接下来固定 A,只换戳法,看响应。</b3>
<svg viewBox="0 0 640 190" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <g data-beat="1" data-obj="system">
    <rect x="30" y="70" width="14" height="60" fill="var(--ink3)"/>
    <rect x="120" y="80" width="52" height="44" rx="6" fill="oklch(0.80 0.09 92)" stroke="currentColor"/>
    <text x="146" y="107" text-anchor="middle" fill="currentColor">块1</text>
    <path d="M 172 102 q 10 -12 20 0 q 10 12 20 0 q 10 -12 20 0 q 10 12 20 0" fill="none" stroke="oklch(0.55 0.13 250)" stroke-width="2"/>
    <rect x="252" y="80" width="52" height="44" rx="6" fill="oklch(0.80 0.09 92)" stroke="currentColor"/>
    <text x="278" y="107" text-anchor="middle" fill="currentColor">块2</text>
    <line x1="304" y1="102" x2="384" y2="102" stroke="currentColor" stroke-width="2"/>
    <rect x="384" y="70" width="14" height="60" fill="var(--ink3)"/>
  </g>
  <g data-beat="2" data-obj="system">
    <text x="146" y="152" text-anchor="middle" fill="oklch(0.62 0.13 250)" font-size="12">A₁₁:挂墙的刚度</text>
    <text x="238" y="152" text-anchor="middle" fill="oklch(0.62 0.13 250)" font-size="12">A₁₂:中间耦合</text>
    <text x="480" y="60" fill="currentColor" font-size="15" font-family="var(--mono)">A·x = b</text>
    <text x="480" y="84" fill="var(--ink3)" font-size="12">已知规则和结果,</text>
    <text x="480" y="102" fill="var(--ink3)" font-size="12">反推位移。</text>
  </g>
  <g data-beat="3" data-obj="source">
    <path d="M 146 26 L 146 72" stroke="oklch(0.68 0.15 55)" stroke-width="3" marker-end="url(#arP2)"/>
    <path d="M 278 26 L 278 72" stroke="oklch(0.68 0.15 55)" stroke-width="3" marker-end="url(#arP2)"/>
    <text x="162" y="20" fill="oklch(0.68 0.15 55)" font-size="12">F₁(源,橙)</text>
    <text x="292" y="20" fill="oklch(0.68 0.15 55)" font-size="12">F₂</text>
    <defs><marker id="arP2" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="oklch(0.68 0.15 55)"/></marker></defs>
  </g>
</svg>
```

```notes
矩阵与逆,最少必要版:
- 矩阵 $A$ 乘向量 = 一种"线性混合"。
- $A\,x=b$:已知混合规则 $A$ 和结果 $b$,反推原料 $x$。
- 反推的机器叫逆矩阵 $A^{-1}$:$x=A^{-1}b$,满足 $A\,A^{-1}=I$(单位阵,乘谁不变谁)。
- 本例数值:$A=\begin{pmatrix}3&1\\1&2\end{pmatrix}$——对角线 3、2 = 两块挂墙刚度,非对角 1 = 中间耦合弹簧。
本 Lecture 只需要这些;下面每一处用到,都会带着具体数字走。
```

```sources
S2
```

## P03 · 把"单位敲击"记下来:矩阵逆的真面目 {mode=theater inherits=P02 objects=source,system,response}

```scene
<b1>还是这套弹簧。这次只戳第 1 块:b = (1, 0)。</b1>
<b2>单位力出现(橙 = 源)。</b2>
<svg viewBox="0 0 640 170" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <g data-beat="1" data-obj="system">
    <rect x="30" y="70" width="14" height="60" fill="var(--ink3)"/>
    <rect x="120" y="80" width="52" height="44" rx="6" fill="oklch(0.80 0.09 92)" stroke="currentColor"/>
    <text x="146" y="107" text-anchor="middle" fill="currentColor">块1</text>
    <path d="M 172 102 q 10 -12 20 0 q 10 12 20 0 q 10 -12 20 0 q 10 12 20 0" fill="none" stroke="oklch(0.55 0.13 250)" stroke-width="2"/>
    <rect x="252" y="80" width="52" height="44" rx="6" fill="oklch(0.80 0.09 92)" stroke="currentColor"/>
    <text x="278" y="107" text-anchor="middle" fill="currentColor">块2</text>
    <line x1="304" y1="102" x2="384" y2="102" stroke="currentColor" stroke-width="2"/>
    <rect x="384" y="70" width="14" height="60" fill="var(--ink3)"/>
  </g>
  <g data-beat="2" data-obj="source">
    <path d="M 146 34 L 146 74" stroke="oklch(0.68 0.15 55)" stroke-width="3.5" marker-end="url(#arP3a)"/>
    <text x="160" y="28" fill="oklch(0.68 0.15 55)" font-size="12">单位力 b₁ = 1</text>
    <defs><marker id="arP3a" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="oklch(0.68 0.15 55)"/></marker></defs>
  </g>
</svg>
```

```predict
只戳块 1(向右推),平衡后块 2 会往哪边走?
- → 和块 1 同向
- 不动
- [x] ← 反向:中间弹簧的状态把块 2 往回带
?? 猜完看下一拍。数字会告诉你:−0.2。
```

```scene
<b1>块 1 向右移动 +0.4。(蓝 = 位移)</b1>
<b2>注意:块 2 向反方向移动 −0.2。单个数字也是一条"响应"。</b2>
<b3>把两个响应数竖着写:这一列就是"戳块 1 的完整响应"。</b3>
<b4>再戳第 2 块:b = (0, 1)。同一套弹簧,换一个敲法。</b4>
<b5>两列并排,括起来——它就是 A⁻¹。矩阵逆是看着长出来的。</b5>
<svg viewBox="0 0 640 230" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <g data-beat="1" data-obj="system">
    <rect x="30" y="120" width="14" height="60" fill="var(--ink3)"/>
    <rect x="120" y="130" width="52" height="44" rx="6" fill="oklch(0.80 0.09 92)" stroke="currentColor"/>
    <text x="146" y="157" text-anchor="middle" fill="currentColor">块1</text>
    <path d="M 172 152 q 10 -12 20 0 q 10 12 20 0 q 10 -12 20 0 q 10 12 20 0" fill="none" stroke="oklch(0.55 0.13 250)" stroke-width="2"/>
    <rect x="252" y="130" width="52" height="44" rx="6" fill="oklch(0.80 0.09 92)" stroke="currentColor"/>
    <text x="278" y="157" text-anchor="middle" fill="currentColor">块2</text>
    <line x1="304" y1="152" x2="384" y2="152" stroke="currentColor" stroke-width="2"/>
    <rect x="384" y="120" width="14" height="60" fill="var(--ink3)"/>
  </g>
  <g data-beat="2" data-obj="response" data-fx="growx">
    <path d="M 120 208 L 198 208" stroke="oklch(0.72 0.12 250)" stroke-width="3" marker-end="url(#arP3b)"/>
    <text x="159" y="226" text-anchor="middle" fill="oklch(0.55 0.13 250)" font-size="12">块1 位移 +0.4</text>
    <defs><marker id="arP3b" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="oklch(0.72 0.12 250)"/></marker></defs>
  </g>
  <g data-beat="3" data-obj="response" data-fx="growx">
    <path d="M 304 208 L 252 208" stroke="oklch(0.72 0.12 250)" stroke-width="3" marker-end="url(#arP3c)"/>
    <text x="286" y="226" text-anchor="middle" fill="oklch(0.55 0.13 250)" font-size="12">块2 位移 −0.2(反向!)</text>
    <defs><marker id="arP3c" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="oklch(0.72 0.12 250)"/></marker></defs>
  </g>
  <g data-beat="4" data-obj="response">
    <rect x="452" y="96" width="120" height="84" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
    <text x="512" y="126" text-anchor="middle" fill="var(--blue-ink)" font-size="14" font-family="var(--mono)">( +0.4 )</text>
    <text x="512" y="150" text-anchor="middle" fill="var(--blue-ink)" font-size="14" font-family="var(--mono)">( −0.2 )</text>
    <text x="512" y="172" text-anchor="middle" fill="var(--ink3)" font-size="10.5">戳块1的响应 = 一列</text>
  </g>
  <g data-beat="5" data-obj="source">
    <path d="M 278 84 L 278 124" stroke="oklch(0.68 0.15 55)" stroke-width="3.5" marker-end="url(#arP3a)"/>
    <text x="292" y="78" fill="oklch(0.68 0.15 55)" font-size="12">b₂ = 1</text>
    <rect x="444" y="8" width="136" height="56" rx="8" fill="none" stroke="var(--amber)" stroke-dasharray="5 4"/>
    <text x="512" y="32" text-anchor="middle" fill="oklch(0.62 0.13 60)" font-size="13" font-family="var(--mono)">A⁻¹ = [列1 | 列2]</text>
    <text x="512" y="52" text-anchor="middle" fill="var(--ink3)" font-size="10.5">两列并排 = 响应表</text>
  </g>
</svg>
```

数值自查(dossier V-03,实算):$A\cdot A^{-1}=I$;$b=(1,0)$ 时 $x=(0.4,-0.2)$,与图中一致。[C003]

一个像,一个坑:
- 像:这张表只依赖系统($A$),不依赖你之后想戳什么。存一次,到处用。
- 坑:若 $A$ 不可逆,"单位敲击响应"根本定义不下来——P18 会回来。

```sources
S2 S3
```

## P04 · 任意源 = 一排单位敲击 {mode=theater inherits=P02 objects=source,system,response}

```scene
<b1>把戳块 1 的力加倍:2·e₁。注意左边的图和右边的数。</b1>
<b2>响应也精确加倍——"线性"的全部意思。</b2>
<b3>再在块 2 上戳 3 份:3·e₂。</b3>
<b4>块 2 的响应同样放大 3 倍。</b4>
<b5>两组力同时作用:两个位移直接相加。总响应 = 查表相加。</b5>
<svg viewBox="0 0 640 260" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <g data-beat="1" data-obj="system">
    <rect x="30" y="150" width="14" height="60" fill="var(--ink3)"/>
    <rect x="120" y="160" width="52" height="44" rx="6" fill="oklch(0.80 0.09 92)" stroke="currentColor"/>
    <text x="146" y="187" text-anchor="middle" fill="currentColor">块1</text>
    <path d="M 172 182 q 10 -12 20 0 q 10 12 20 0 q 10 -12 20 0 q 10 12 20 0" fill="none" stroke="oklch(0.55 0.13 250)" stroke-width="2"/>
    <rect x="252" y="160" width="52" height="44" rx="6" fill="oklch(0.80 0.09 92)" stroke="currentColor"/>
    <text x="278" y="187" text-anchor="middle" fill="currentColor">块2</text>
    <line x1="304" y1="182" x2="384" y2="182" stroke="currentColor" stroke-width="2"/>
    <rect x="384" y="150" width="14" height="60" fill="var(--ink3)"/>
  </g>
  <g data-beat="2" data-obj="source">
    <path d="M 146 96 L 146 154" stroke="oklch(0.68 0.15 55)" stroke-width="4" marker-end="url(#arP4a)"/>
    <text x="160" y="90" fill="oklch(0.68 0.15 55)" font-size="12">2·e₁</text>
    <defs><marker id="arP4a" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="oklch(0.68 0.15 55)"/></marker></defs>
  </g>
  <g data-beat="3" data-obj="response" data-fx="growx">
    <path d="M 172 182 L 292 182" stroke="oklch(0.72 0.12 250)" stroke-width="3.5" marker-end="url(#arP4b)"/>
    <text x="230" y="172" text-anchor="middle" fill="oklch(0.55 0.13 250)" font-size="12">+0.8(= 2 × 0.4)</text>
    <defs><marker id="arP4b" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="oklch(0.72 0.12 250)"/></marker></defs>
  </g>
  <g data-beat="4" data-obj="source">
    <path d="M 278 96 L 278 154" stroke="oklch(0.68 0.15 55)" stroke-width="4.5" marker-end="url(#arP4a)"/>
    <text x="292" y="90" fill="oklch(0.68 0.15 55)" font-size="12">3·e₂</text>
  </g>
  <g data-beat="5" data-obj="response" data-fx="growx">
    <path d="M 252 182 L 172 182" stroke="oklch(0.72 0.12 250)" stroke-width="3.5" marker-end="url(#arP4c)"/>
    <text x="212" y="200" text-anchor="middle" fill="oklch(0.55 0.13 250)" font-size="12">−0.6(= 3 × −0.2)</text>
    <defs><marker id="arP4c" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="oklch(0.72 0.12 250)"/></marker></defs>
    <rect x="440" y="96" width="170" height="130" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
    <text x="525" y="126" text-anchor="middle" fill="var(--blue-ink)" font-size="13" font-family="var(--mono)">x = 2·col₁ + 3·col₂</text>
    <text x="525" y="152" text-anchor="middle" fill="var(--blue-ink)" font-size="13" font-family="var(--mono)">= 2(0.4,−0.2)</text>
    <text x="525" y="174" text-anchor="middle" fill="var(--blue-ink)" font-size="13" font-family="var(--mono)"> + 3(−0.2,0.6)</text>
    <text x="525" y="202" text-anchor="middle" fill="var(--ink3)" font-size="11">= (0.2, 1.4) · 图形相加 = 数字相加</text>
  </g>
</svg>
```

x 的数值自查:$x=A^{-1}b=\frac15\begin{pmatrix}2&-1\\-1&3\end{pmatrix}\begin{pmatrix}2\\3\end{pmatrix}=(0.2,\,1.4)$,与图中一致。[C002,C003]

这就是"查表相加"合法的全部理由:线性。
非线性系统里这条路直接断掉——P18 会专门讲。

```sources
S2 S17
```

## P05 · 从两个自由度到一根连续的弦 {mode=theater inherits=P02 objects=source,delta}

先猜再看:下面把"一个点的单位力"逐步压窄。宽度压成一半、面积保持 1,高度应该怎么变?

```predict
矩形宽度压成一半,为了保持面积 = 1,高度应该?
- [x] ×2:面积 = 宽 × 高,宽减半则高加倍
- 不变:高度和宽度无关
- ×½:跟着一起变小
?? 每次都猜一下——"变的是什么、不变的是什么"是这一页唯一的看点。
```

```scene
<b1>一个单位力,铺在宽 w 上。盯住金色的"面积 = 1"——它全程不变。</b1>
<b2>宽度压一半,高度加倍。面积还是 1。</b2>
<b3>再压一半,再翻倍。</b3>
<b4>极限:无限窄、无限高、面积恒 1。它就是 δ(x−x′)——连续世界的"单位敲击"。</b4>
<svg viewBox="0 0 640 240" style="color:var(--ink);font-family:var(--sans)" font-size="12">
  <g data-beat="1" data-obj="source">
    <line x1="30" y1="185" x2="190" y2="185" stroke="currentColor"/>
    <rect x="88" y="105" width="44" height="80" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
    <text x="110" y="205" text-anchor="middle" fill="var(--ink3)">宽 w</text>
    <text x="110" y="95" text-anchor="middle" fill="var(--ink3)">高 1/w</text>
    <rect x="30" y="18" width="160" height="30" rx="8" fill="none" stroke="oklch(0.68 0.13 92)" stroke-width="2"/>
    <text x="110" y="38" text-anchor="middle" fill="oklch(0.55 0.12 92)" font-size="13" font-family="var(--mono)">面积 = 1(不变)</text>
  </g>
  <g data-beat="2" data-obj="delta">
    <line x1="230" y1="185" x2="390" y2="185" stroke="currentColor"/>
    <rect x="296" y="65" width="28" height="120" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
    <text x="310" y="205" text-anchor="middle" fill="var(--ink3)">w/2</text>
  </g>
  <g data-beat="3" data-obj="delta">
    <line x1="430" y1="185" x2="590" y2="185" stroke="currentColor"/>
    <rect x="500" y="25" width="20" height="160" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
    <text x="510" y="205" text-anchor="middle" fill="var(--ink3)">w/4</text>
  </g>
  <g data-beat="4" data-obj="delta">
    <path d="M 596 185 L 602 10 L 608 185 Z" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
    <text x="560" y="30" fill="oklch(0.55 0.12 92)" font-size="13" font-family="var(--mono)">→ δ(x−x′)</text>
  </g>
</svg>
```

于是离散的"第 $j$ 列响应表"升级为连续的**二元函数**:
$G(x,\,x')$ = 在 $x'$ 敲一下、在 $x$ 处的响应。全文角色色固定:源橙、响应蓝、δ 金、G 深蓝。

```sources
S3 S18
```

## P06 · Formula Anatomy:G(x, x') 每个符号是什么

| 符号 | 含义 | 备注 |
|---|---|---|
| $x$ | 观察点(我要算响应的位置) | 自变量 |
| $x'$ | 敲击点(源所在的位置) | 自变量,注意撇号 |
| $G$ | **单位**敲击在 $x'$、观察在 $x$ 的响应 | 它自己不是力,也不是位移 |
| 依赖 | 只依赖系统本身 + 边界条件 | 与你之后加什么源无关 |

三件立刻能说的事:

1. **输入**:一个点源的位置 $x'$;**输出**:全场响应 $x\mapsto G(x,x')$。
2. **量纲**(认真对待,这是个坑):本 Lecture 的弦方程用**归一化模型**——张力 $T=1$ 已被吸收进算符,一切用**约化单位**。此时 $L=-\frac{d^2}{dx^2}$ 的作用是 1/长度²,右端 δ 也是 1/长度,于是 $[G]=$ 长度,$[f]=1/$ 长度,$[G]\times[f]=$ 长度 = $[u]$,自洽。若写回**物理单位**的弦 $-T\,u''=q$($[T]=$ N,$[q]=$ N/m),则 $[G]=\mathrm{m/N}$。两种写法都对;混着写才是错——我们全文只用归一化版,并在 P10 的表里注明。[C004]
3. **角色**:它是"系统的指纹"。两根不同的弦,即使方程长得一样,弦的松紧不同,$G$ 就不同。

$G$ 的正式名字:格林函数。为什么叫这个名字,P07 讲完定义你就不会再问。[C001]

```visual
<svg viewBox="0 0 640 130" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <line x1="60" y1="80" x2="580" y2="80" stroke="currentColor" stroke-width="2"/>
  <circle cx="180" cy="80" r="9" fill="oklch(0.68 0.15 55)"/>
  <text x="180" y="112" text-anchor="middle" fill="oklch(0.68 0.15 55)" font-size="13">x′(敲击点)</text>
  <circle cx="460" cy="80" r="9" fill="none" stroke="oklch(0.72 0.12 250)" stroke-width="3"/>
  <text x="460" y="112" text-anchor="middle" fill="oklch(0.55 0.13 250)" font-size="13">x(观察点)</text>
  <path d="M 195 66 C 280 20 380 20 448 64" fill="none" stroke="oklch(0.5 0.14 260)" stroke-width="2.5" marker-end="url(#arP6)"/>
  <defs><marker id="arP6" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="oklch(0.5 0.14 260)"/></marker></defs>
  <text x="318" y="36" text-anchor="middle" fill="oklch(0.5 0.14 260)" font-size="14" font-family="var(--mono)">G(x, x′)</text>
  <text x="318" y="62" text-anchor="middle" fill="var(--ink3)" font-size="11">在 x′ 敲一下 → 在 x 看响应;两个自变量,缺一不可</text>
</svg>
```


```sources
S2 S3
```

## P07 · 现在,LG = δ 才自然出现 {mode=derive inherits=P05 objects=delta,kernel}

真正的视觉证明:不看定义,**从 G 出发,两次求导,亲手把 δ 画出来**。

```scene
<b1>这是 G:单位敲击的响应,一座三角帆。(深蓝 = 核)</b1>
<b2>对 x 求一次导:左段斜率 +0.5,右段 −0.5。</b2>
<b3>再求一次导:两段各自变成 0——除了一点,处处为零。</b3>
<b4>那"一点"呢?斜率从 +0.5 跳到 −0.5,跳了 −1:这里竖起一根金色尖峰。</b4>
<b5>把四拍连起来读:负号让跳跃方向对上。LG = δ 不是定义,是读出来的。</b5>
<svg viewBox="0 0 640 300" style="color:var(--ink);font-family:var(--sans)" font-size="12">
  <defs><marker id="arP7s" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="var(--ink3)"/></marker></defs>
  <line x1="40" y1="150" x2="600" y2="150" stroke="var(--ink3)" stroke-width="1.5"/>
  <g data-beat="1" data-obj="kernel">
    <path d="M 40 150 L 320 84 L 600 150" fill="none" stroke="oklch(0.5 0.14 260)" stroke-width="3"/>
    <text x="430" y="66" fill="oklch(0.5 0.14 260)" font-size="13">G(x, x′):三角帆(深蓝 = 核)</text>
    <line x1="320" y1="84" x2="320" y2="150" stroke="var(--ink3)" stroke-dasharray="3 4"/>
    <text x="332" y="120" fill="var(--ink3)" font-size="11">x′(敲击点)</text>
  </g>
  <g data-beat="2">
    <path d="M 60 138 L 280 138" stroke="oklch(0.68 0.15 55)" stroke-width="2"/>
    <text x="150" y="130" fill="oklch(0.68 0.15 55)" font-size="11">G′ = +0.5</text>
    <path d="M 360 162 L 580 162" stroke="oklch(0.68 0.15 55)" stroke-width="2"/>
    <text x="470" y="180" fill="oklch(0.68 0.15 55)" font-size="11">G′ = −0.5</text>
    <path d="M 300 138 L 340 162" stroke="var(--ink3)" stroke-dasharray="4 3" marker-end="url(#arP7s)"/>
    <text x="320" y="210" text-anchor="middle" fill="var(--ink3)">一次导数:斜率图(折点 = 跳变处)</text>
  </g>
  <g data-beat="3">
    <line x1="60" y1="248" x2="580" y2="248" stroke="oklch(0.6 0.02 60)" stroke-width="2.5"/>
    <text x="90" y="238" fill="var(--ink3)" font-size="11">G″ = 0(左段)</text>
    <text x="520" y="238" fill="var(--ink3)" font-size="11">G″ = 0(右段)</text>
  </g>
  <g data-beat="4" data-obj="delta">
    <path d="M 314 262 L 320 220 L 326 262 Z" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
    <text x="352" y="236" fill="oklch(0.55 0.12 92)" font-size="12">斜率跳 −1 → 尖峰 δ(x−x′)</text>
  </g>
  <g data-beat="5" data-obj="delta">
    <rect x="150" y="20" width="340" height="0" fill="none"/>
    <text x="320" y="286" text-anchor="middle" fill="currentColor" font-size="15" font-family="var(--mono)">−G″ = δ   ⇒   L G = δ</text>
  </g>
</svg>
```

离散对照一模一样:$A\,g_j=e_j$(第 $j$ 列)。连续版只是把"列"换成"$x'$"。这行等式就是格林函数的定义 [C001]。

```notes
- 微分算符,一句话:$L=-\frac{d^2}{dx^2}$ 读作"微分两次再变号"。鼓包越尖,作用越猛。
- 符号为什么带负号:开口向上的抛物线二阶导为正;弦的势能要求"鼓包向下凹",
  所以定义 $L$ 带负号,让 $-G''$ 在折点处给出**正**强度的 δ(斜率从 +0.5 跳到 −0.5,
  跳跃 = −1;$-G''$ 的强度 = +1)。若不带负号,得把 δ 写成负的——约定而已,但要一致用到底。
- "指定边界条件下"六个字不可省:方程只定半个 G,另一半由边界定(P08)。
```

```sources
S2 S3 S10
```

## P08 · 边界条件:G 是一族函数,不是一条

要唯一确定一个 G,方程 $LG=\delta$ 只给了一半,另一半由**问题的类型**决定 [C001]。分两类,别混:

**静态问题**(弦、静电、静弹性):$L$ + **边界条件**。

- 两端**固定**(弦):$G(0)=G(1)=0$ → 三角帆形(P09)
- 一端自由(杆):一端 $G=0$,另一端斜率为零
- **整个实轴(无边界)**:这时 $-d^2/dx^2$ 的基本解是 $G=\frac{1}{2}|x-x'|$ 附近的一族——
  它随距离**线性增长**,根本不衰减!想让它收敛,必须人为加一个归一化条件(比如要求 $G$ 在某点为零)或换成有限域。[C021]
  这是最容易踩的坑:**"无限长 + 衰减"对静态 1D Laplace 算符根本不成立**。

**含时问题**(波、热、量子):$L$ + **初始条件** + **因果约定**。

- 这才轮到"推迟/超前"出场:推迟 G 只在源**之后**响应,超前 G 只在源**之前**。
- 因果选择是**时间**问题的专利。把它塞进静态例子(比如 P13 的静电),是常见错误。[C012]

```visual
<svg viewBox="0 0 640 210" style="color:var(--ink);font-family:var(--sans)" font-size="12">
  <text x="160" y="26" text-anchor="middle" fill="currentColor" font-size="13">静态:L + 边界条件</text>
  <rect x="60" y="40" width="200" height="120" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <path d="M 90 140 L 160 66 L 230 140" fill="none" stroke="oklch(0.62 0.13 250)" stroke-width="2.5"/>
  <text x="160" y="150" text-anchor="middle" fill="var(--ink3)" font-size="11">两端固定 → 三角帆</text>
  <text x="480" y="26" text-anchor="middle" fill="currentColor" font-size="13">含时:L + 初值 + 因果约定</text>
  <rect x="380" y="40" width="200" height="120" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <path d="M 400 120 L 440 120 L 470 84 L 500 84 L 530 60 L 560 60" fill="none" stroke="oklch(0.62 0.13 250)" stroke-width="2.5"/>
  <text x="480" y="150" text-anchor="middle" fill="var(--ink3)" font-size="11">推迟支:波纹只向未来扩</text>
  <text x="320" y="200" text-anchor="middle" fill="var(--ink3)">同一句口诀:方程给一半,条件给另一半</text>
</svg>
```

```callout 账本高频误区 [C016]
"G 就是一条公式"是错的。正确说法:**L + 边界条件(静态)或 L + 初值 + 因果约定(含时),共同唯一确定一个 G。**
Physics SE 高赞问题里,"为什么我的 G 和书上的不一样"的答案几乎都是:边界或因果约定不同。
```

所以后面每讲一个领域的 G,第一句话都是:什么域、什么边界、静态还是含时。[C016]

```sources
S2 S10 S18
```

## P09 · 完整例题:两端固定弦,一算到底

把 P01 的弦正式做掉。域 $[0,1]$,边界 $G(0,x')=G(1,x')=0$:

$$L=-\frac{d^2}{dx^2},\qquad L\,G=\delta(x-x')$$

**第一步:除敲击点外,G 是直线。** 因为 $G''=0$ 的解就是一次函数。

**第二步:两端贴零。** 左段直线要过 $(0,0)$ → 左段 $=c_L\,x$;右段过 $(1,0)$ → 右段 $=c_R\,(1-x)$。

**第三步:连接条件。** G 本身在 $x'$ 处连续(弦不断),但斜率要**向下跳 1**——
这正是 δ 的强度(把方程从 $x'-\epsilon$ 积到 $x'+\epsilon$:$-G'|_{-}^{+}=1$)。

解出三件事:连续、斜率跳 1、两端为零。得:

$$\boxed{\;G(x,x')=\min(x,x')\,\bigl(1-\max(x,x')\bigr)\;}$$

自查(dossier V-01,实算):折点左斜率 $+0.5$、右斜率 $-0.5$、跳跃 $-1$——与 δ 强度一致。✓

**用它干活**:整根弦均匀受载 $f\equiv 1$:

$$u(x)=\int_0^1 G(x,x')\,dx'=\frac{x(1-x)}{2}$$

数值复核(dossier V-02):$\int G(0.5,x')dx' = 0.125000$,解析 $u(0.5)=0.125$。✓

**动手玩** [C004,C005]:

```lab
<div class="cap"><b>你在看什么:</b>蓝线是"在 <span id="lx">0.5</span> 处敲一下,整根弦的响应 G(x,x')(乘了系数放大到可见)。
拖动滑块移动敲击点——注意三角形永远指向敲击处、两端钉死。勾选后叠加第二个橙色源:两个响应直接相加(线性)。</div>
<canvas id="g1" height="240"></canvas>
<div class="ctrls">
  <div class="ctrl"><label>敲击位置 x′<span class="v" id="v1">0.50</span></label>
    <input type="range" id="s1" min="0.05" max="0.95" step="0.01" value="0.5"></div>
  <div class="ctrl"><label>第二个源 x′′(关闭=只看单源)<span class="v" id="v2">0.75</span></label>
    <input type="range" id="s2" min="0.05" max="0.95" step="0.01" value="0.75"></div>
</div>
<div class="btns"><button id="b2">叠加第二个源:开</button><button id="br">重置</button></div>
<div class="readout" id="ro"></div>
<script>
"use strict";
(()=>{const cv=document.getElementById("g1");if(!cv)return;
 window.addEventListener("error",e=>{const r=document.getElementById("ro");
   if(r)r.textContent="ERR:"+e.message;});
 const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
 let d=window.devicePixelRatio||1,W=0,H=+cv.getAttribute("height"),ctx;
 function fit(){d=window.devicePixelRatio||1;W=cv.clientWidth;cv.width=W*d;cv.height=H*d;
   ctx=cv.getContext("2d");ctx.setTransform(d,0,0,d,0,0);}
 function redraw(){fit();draw();}
 window.addEventListener("resize",redraw);
 window.addEventListener("lecturepage",redraw);
 const S={a:0.5,b:0.75,two:false};
 const G=(x,xp)=>Math.min(x,xp)*(1-Math.max(x,xp));
 function draw(){
   if(W===0)return;
   ctx.fillStyle="#191d2b";ctx.fillRect(0,0,W,H);
   const pad=10,m=H-30,base=m;
   const X=x=>pad+x*(W-2*pad), Y=u=>base-u*160;
   ctx.strokeStyle="#3a4160";ctx.beginPath();ctx.moveTo(X(0),base);ctx.lineTo(X(1),base);ctx.stroke();
   ctx.strokeStyle="#5d6fa8";ctx.lineWidth=1;
   for(let k=1;k<=4;k++){ctx.beginPath();ctx.moveTo(X(0),base-k*40);ctx.lineTo(X(1),base-k*40);ctx.stroke();}
   const u=x=>G(x,S.a)+(S.two?0.7*G(x,S.b):0);
   ctx.strokeStyle="oklch(0.8 0.13 250)";ctx.lineWidth=2.2;ctx.beginPath();
   for(let i=0;i<=400;i++){const x=i/400;i?ctx.lineTo(X(x),Y(u(x))):ctx.moveTo(X(x),Y(u(x)));}
   ctx.stroke();ctx.lineWidth=1;
   ctx.fillStyle="oklch(0.85 0.14 92)";ctx.beginPath();ctx.arc(X(S.a),Y(G(S.a,S.a)),5,0,7);ctx.fill();
   if(S.two){ctx.fillStyle="oklch(0.78 0.14 60)";ctx.beginPath();ctx.arc(X(S.b),Y(u(S.b)),5,0,7);ctx.fill();}
   document.getElementById("ro").textContent="u_max = "+u(S.a).toFixed(3)+"(相对单位)";
 }
 document.getElementById("s1").addEventListener("input",e=>{S.a=clamp(+e.target.value,0.05,0.95);
   document.getElementById("v1").textContent=S.a.toFixed(2);document.getElementById("lx").textContent=S.a.toFixed(2);draw();});
 document.getElementById("s2").addEventListener("input",e=>{S.b=clamp(+e.target.value,0.05,0.95);
   document.getElementById("v2").textContent=S.b.toFixed(2);draw();});
 document.getElementById("b2").addEventListener("click",function(){S.two=!S.two;
   this.textContent=S.two?"叠加第二个源:关":"叠加第二个源:开";draw();});
 document.getElementById("br").addEventListener("click",()=>{S.a=0.5;S.b=0.75;S.two=false;
   document.getElementById("s1").value=0.5;document.getElementById("s2").value=0.75;
   document.getElementById("v1").textContent="0.50";document.getElementById("v2").textContent="0.75";draw();});
 draw();
})();
</script>
```

这个三角形是整个 Lecture 的"核心图像",后面每个领域都是它的变体。

```sources
S2 S18
```

## P10 · 普遍公式:u(x) = ∫ G(x,x') f(x') dx'

把 P04 的离散故事翻译回连续世界:

$$u(x)=\int G(x,x')\,f(x')\,dx'$$

| 符号 | 含义 | 量纲(归一化模型,T=1) |
|---|---|---|
| $f(x')$ | 外部源(每单位长度的源强度) | 1/m |
| $dx'$ | 一个微小源区域 | m |
| $G(x,x')$ | 单位点源的响应核 | m |
| $G(x,x')\,f(x')\,dx'$ | 这个小源区域贡献给 $x$ 的响应 | m |
| $u(x)$ | 全部小源响应的叠加 | m |

自洽核对:$[G]\,[f]\,[dx'] = \mathrm{m}\cdot\tfrac{1}{\mathrm{m}}\cdot\mathrm{m}=\mathrm{m}=[u]$。✓(dossier V-04)

> 写回物理单位的弦 $-T\,u''=q$($[T]=\mathrm{N}$,$[q]=\mathrm{N/m}$):$[G]=\mathrm{m/N}$。
> 结构一模一样,$T$ 只是坐进了算符。全文其余页面沿用归一化模型。

```visual
<svg viewBox="0 0 640 140" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <defs><marker id="arP10" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="var(--ink3)"/></marker></defs>
  <rect x="30" y="40" width="150" height="56" rx="8" fill="oklch(0.95 0.04 55)" stroke="oklch(0.68 0.15 55)"/>
  <text x="105" y="64" text-anchor="middle" fill="currentColor">源 f(x′)</text>
  <text x="105" y="84" text-anchor="middle" fill="var(--ink3)" font-size="11">橙:切成小敲击</text>
  <rect x="245" y="40" width="150" height="56" rx="8" fill="oklch(0.93 0.05 260)" stroke="oklch(0.5 0.14 260)"/>
  <text x="320" y="64" text-anchor="middle" fill="currentColor">查表 G(x,x′)</text>
  <text x="320" y="84" text-anchor="middle" fill="var(--ink3)" font-size="11">深蓝:单位敲击响应</text>
  <rect x="460" y="40" width="150" height="56" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <text x="535" y="64" text-anchor="middle" fill="currentColor">响应 u(x)</text>
  <text x="535" y="84" text-anchor="middle" fill="var(--ink3)" font-size="11">蓝:全部相加</text>
  <line x1="180" y1="68" x2="240" y2="68" stroke="var(--ink3)" stroke-width="1.6" marker-end="url(#arP10)"/>
  <line x1="395" y1="68" x2="455" y2="68" stroke="var(--ink3)" stroke-width="1.6" marker-end="url(#arP10)"/>
  <text x="320" y="124" text-anchor="middle" fill="var(--ink3)" font-size="12">这套"橙→深蓝→蓝"的流水线,从 P02 到 P17 不换色</text>
</svg>
```



四个性质,逐条对应你已见过的东西:

1. 源加倍 → 响应加倍($G$ 不变)。
2. 源移动 → $G$ 的三角帆整体平移(在平移不变的域里,P11)。
3. 两个源 → 两个响应相加(P09 的交互演示过)。
4. $f=\delta(x-x_0)$ 代回去 → $u(x)=G(x,x_0)$。**定义自动被公式包含。** [C005]

一句话:这个积分就是"查表相加"的连续版。$G$ 是表,$f$ 是权重,$u$ 是总和。

```sources
S2 S17
```

## P11 · 平移不变的世界:卷积与傅里叶 {mode=derive inherits=P05 objects=source,response}

先猜再看:实空间里卷积是"逐点扫过整个域"。什么对称性让它在另一个世界里变成乘法?

```predict
什么性质使卷积在傅里叶世界里变成乘法?
- [x] 平移不变:源挪个位置,响应只是跟着挪,形状不变
- 能量守恒:总量不会凭空消失
- 边界为零:两端钉死
?? P08 的"无限长/周期域"就是平移不变。有它,G 只依赖差,卷积才退化为乘法。
```

```scene
<b1>任意载荷 f:切成一排小敲击。(橙 = 每个小源)</b1>
<b2>每个小敲击 → 自己的小三角响应:形状相同,位置跟着源走,高矮跟着强度走。</b2>
<b3>全部相加:蓝色曲线就是 u(x)。卷积 = 查表相加。</b3>
<svg viewBox="0 0 640 220" style="color:var(--ink);font-family:var(--sans)" font-size="12">
  <line x1="40" y1="160" x2="600" y2="160" stroke="var(--ink3)" stroke-width="1.5"/>
  <g data-beat="1" data-obj="source">
    <path d="M 90 160 L 90 120 L 96 160 Z" fill="oklch(0.68 0.15 55)"/>
    <path d="M 210 160 L 216 100 L 222 160 Z" fill="oklch(0.68 0.15 55)"/>
    <path d="M 330 160 L 336 132 L 342 160 Z" fill="oklch(0.68 0.15 55)"/>
    <path d="M 450 160 L 456 108 L 462 160 Z" fill="oklch(0.68 0.15 55)"/>
    <text x="320" y="200" text-anchor="middle" fill="var(--ink3)">f(x′):一排小敲击,高矮 = 强度</text>
  </g>
  <g data-beat="2" data-obj="response">
    <path d="M 50 160 L 90 128 L 130 160" fill="none" stroke="oklch(0.72 0.12 250)" stroke-width="1.6"/>
    <path d="M 176 160 L 216 76 L 256 160" fill="none" stroke="oklch(0.72 0.12 250)" stroke-width="1.6"/>
    <path d="M 296 160 L 336 118 L 376 160" fill="none" stroke="oklch(0.72 0.12 250)" stroke-width="1.6"/>
    <path d="M 416 160 L 456 84 L 496 160" fill="none" stroke="oklch(0.72 0.12 250)" stroke-width="1.6"/>
    <text x="560" y="90" fill="oklch(0.55 0.13 250)" font-size="12">每个源的小三角</text>
  </g>
  <g data-beat="3" data-obj="response" data-fx="grow">
    <path d="M 40 160 C 120 150 180 120 240 106 C 300 96 340 96 400 88 C 470 78 540 118 600 138" fill="none" stroke="oklch(0.55 0.13 250)" stroke-width="3"/>
    <text x="320" y="60" text-anchor="middle" fill="oklch(0.55 0.13 250)" font-size="13">u(x) = ∫ G(x,x′) f(x′) dx′(全部相加)</text>
  </g>
</svg>
```

```scene
<b1>换到傅里叶世界:每个波长一个坐标。微分变乘法,卷积变乘法。</b1>
<b2>解微分方程降级为做一次除法。P17 的量子器件仿真,就是这里的工业版。</b2>
<svg viewBox="0 0 640 150" style="color:var(--ink);font-family:var(--sans)" font-size="12">
  <defs><marker id="arP11" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="var(--ink3)"/></marker></defs>
  <rect x="40" y="30" width="180" height="56" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <text x="130" y="54" text-anchor="middle" fill="currentColor" font-family="var(--mono)">u = G ⊛ f</text>
  <text x="130" y="74" text-anchor="middle" fill="var(--ink3)" font-size="11">实空间:逐点卷积</text>
  <rect x="420" y="30" width="180" height="56" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <text x="510" y="54" text-anchor="middle" fill="currentColor" font-family="var(--mono)">Û(k) = Ĝ(k)·f̂(k)</text>
  <text x="510" y="74" text-anchor="middle" fill="var(--ink3)" font-size="11">k 空间:逐点乘法</text>
  <path d="M 224 58 L 414 58" stroke="var(--ink3)" stroke-width="1.6" marker-end="url(#arP11)"/>
  <text x="318" y="46" text-anchor="middle" fill="oklch(0.62 0.13 250)" font-size="11">平移不变 ⇒ 傅里叶变换</text>
  <text x="320" y="124" text-anchor="middle" fill="var(--ink3)">帽子 = 变换后的像。对称性把"解方程"降级成"做除法"</text>
</svg>
```

```notes
傅里叶变换,最少必要版:把函数看成不同波长正弦波的叠加;变换 = 换坐标,
从"每个位置的值"换成"每个波长的振幅"。两条 magic:微分变乘法($\partial_x\to ik$),
卷积变乘法。用到 $L\,G=\delta$:δ 的像是常数 1,故 $\hat G(k)=1/\hat L(k)$。
对 $L=-\frac{d^2}{dx^2}+m^2$:$\hat L(k)=k^2+m^2$,$\hat G(k)=\frac{1}{k^2+m^2}$。
极限自查:$k\to\infty$ 时 $\hat G\to 0$——尖锐源的高频响应衰减,合理。[C006]
```

```sources
S2 S17
```

## P12 · 一个结构,四具身体

同一套数学结构,在不同学科里各有名字。但它们的"亲疏"不同,分四级说才严谨:

| 名字 | 领域 | "敲一下"是什么 | "响应"是什么 | 与 G 的关系 |
|---|---|---|---|---|
| 矩阵逆的列 | 线性代数 | 单位向量 $e_j$ | 解向量 $x$ | **同一对象的离散/连续两种记法** |
| 冲击响应 $h(t)$ | 信号/电路 | 单位电压脉冲 | 输出波形 | **同一结构**(时域 Green 函数) |
| 传播子 / 核 | 量子/统计 | 一点处的粒子 | 它跑到别处的振幅/概率 | **同一结构 + 因果约定与 convention 因子** |
| 传递函数 | 控制 | —(频域视角) | 频率响应 | **变换域表示**:传递函数 = 冲击响应的傅里叶/拉普拉斯像 |
| 感受率 susceptibility | 统计物理 | 微扰场 | 响应量密度 | **近亲响应函数**:定义与因果结构随领域约定而变 |

一句话分级:**有的是同一个对象换记法,有的是同一个结构换表示,有的是变换域里的像,有的是近亲。**[C003,C013]

```visual
<svg viewBox="0 0 640 240" style="color:var(--ink);font-family:var(--sans)" font-size="12">
  <defs><marker id="arC12" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="var(--ink3)"/></marker></defs>
  <rect x="240" y="20" width="160" height="44" rx="22" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <text x="320" y="47" text-anchor="middle" fill="currentColor">线性响应结构</text>
  <text x="320" y="82" text-anchor="middle" fill="var(--ink3)" font-size="11">线性系统 · 单位刺激 · 叠加求和</text>
  <text x="110" y="130" text-anchor="middle" fill="currentColor">矩阵逆的列</text>
  <text x="110" y="146" text-anchor="middle" fill="var(--ink3)" font-size="10.5">同一对象(离散)</text>
  <text x="250" y="130" text-anchor="middle" fill="currentColor">冲击响应 h(t)</text>
  <text x="250" y="146" text-anchor="middle" fill="var(--ink3)" font-size="10.5">同一结构(时域)</text>
  <text x="390" y="130" text-anchor="middle" fill="currentColor">传播子</text>
  <text x="390" y="146" text-anchor="middle" fill="var(--ink3)" font-size="10.5">同一结构+因果约定</text>
  <text x="530" y="130" text-anchor="middle" fill="currentColor">传递函数</text>
  <text x="530" y="146" text-anchor="middle" fill="var(--ink3)" font-size="10.5">变换域表示</text>
  <path d="M 320 92 L 110 118" stroke="var(--ink3)" fill="none" marker-end="url(#arC12)"/>
  <path d="M 300 92 L 255 118" stroke="var(--ink3)" fill="none" marker-end="url(#arC12)"/>
  <path d="M 340 92 L 385 118" stroke="var(--ink3)" fill="none" marker-end="url(#arC12)"/>
  <path d="M 380 74 L 528 118" stroke="var(--ink3)" stroke-dasharray="4 3" fill="none" marker-end="url(#arC12)"/>
  <text x="320" y="188" text-anchor="middle" fill="var(--ink3)" font-size="11">虚线 = 差一次傅里叶/拉普拉斯变换;实线 = 换记法或加约定</text>
  <text x="320" y="212" text-anchor="middle" fill="var(--ink3)" font-size="11">susceptibility、影响系数等近亲,同样是"响应函数"家族的方言</text>
</svg>
```

学新领域时先问一句:**这里的"单位敲击"是什么?**常能一步到位。

```sources
S3 S4 S17
```

## P13 · 静电学:你早就在用它

静电势满足 $-\nabla^2\phi=\rho/\varepsilon_0$。这里要区分**两个核**,混用是常见错误:

**数学核(算符 $-\nabla^2$ 的格林函数)**——量纲 1/长度:

$$G_L(\mathbf r,\mathbf r')=\frac{1}{4\pi|\mathbf r-\mathbf r'|},\qquad -\nabla^2 G_L=\delta(\mathbf r-\mathbf r')$$

**物理响应核(单位电荷产生的电势)**——量纲 V/C:

$$K_\phi(\mathbf r,\mathbf r')=\frac{1}{4\pi\varepsilon_0|\mathbf r-\mathbf r'|}$$

关系一句话:$K_\phi = G_L/\varepsilon_0$。物理常数 $\varepsilon_0$ 坐进了算符的倒数里,结构不变。
代入 $u=\int Gf$ 的静电版:任意电荷分布的势 $=$ 每个点电荷的库仑势**求和**。
你从高中就会的"点电荷叠加",底层就是这个核。[C007]

- **Formula anatomy(快版)**:$|\mathbf r-\mathbf r'|$ = 两点距离;$4\pi$ = 三维球面积分常数;
  $K_\phi$ 量纲 = V/C;$\mathbf r'\to\mathbf r$ 时发散 = 点电荷自能发散(物理上用有限半径截断)。
- **极限自查**:$|\mathbf r|\to\infty$,$K_\phi\to 0$——离电荷越远势越弱。✓
- **镜像法**:接地平面旁的点电荷,$G$ = 真电荷 + 一个"假想镜像"的叠加。
  P08 说的"静态问题由边界决定 G",这里是最著名的例子。

```sources
S2 S3
```

## P14 · 弹性力学:Kelvin 解与位错

把"敲一下"换成"在无限大弹性固体里,集中施加一个点力"。
解出的位移场叫 **Kelvin 解**(1848)——弹性世界的 $1/4\pi r$。它就是弹性算符的格林函数。[C008]

发展线:Kelvin(1848)全空间点力 → Boussinesq(1885)表面点力 →
Mindlin(1936)半空间**内部**点力。半空间版本对"地表附近的工程"至关重要。[C009]

**位错应力场的现代算法**:

1. 位错芯写成一组**本征应变**(分布在滑移面附近)。
2. 本征应变等效于一组体力。
3. 应力场 = 体力与应力 Green 函数的卷积(Jin 2009 给了闭式应力 G)。[C010]

一句话:Kelvin 解是所有位错应力场的"印章"。P15 你会看到它在晶体管里的样子。

```sources
S9 S8
```

## P15 · Si/SiGe:晶体管里的格林函数

你的领域,正面使用场景。

**产业事实**:在 pMOS 源/漏嵌入压缩应变的 SiGe,提升空穴迁移率;
Intel 在 90nm 工艺代将 strained silicon 引入量产,90nm 于 2003 年进入生产爬坡
(Intel 官方背景材料 [C011])。

**力学链条**:

```
SiGe 晶格常数 > Si → 界面失配 → 沟道受压应变(迁移率↑)
→ 失配过大时产生失配位错(器件杀手)
→ 位错应力场 = 本征应变 ⊛ 应力 Green 函数(P14 的三步)
→ 解析/半解析路线:线性几何下的快速估计与校验
```

**TCAD 里的真实分工**(据公开文献与厂商文档,厂商内部实现细节不完全公开,可能随版本变化 [C023]):
工业 TCAD 的应力计算主流是**连续介质数值求解**(FEM/工艺仿真,如 Krzeminski 2012 把工艺仿真与实验应力映射对比);
Green 函数卷积走的是**解析/半解析路线**——在几何足够线性、基本解已知的场景里,
它提供快速估计和解析校验,例如量子线结构的应力解析(P14 的 S8 正是为 quantum-wire 结构而写)。
两者是分工,不是替代。

本页刻意不给 SiGe 弹性常数的具体数值(dossier open question:未查证),结构先立住。

科研延伸:各向异性、压电、双材料的 G 有闭式解析(Pan & Chen 专著),
是半导体力学解析计算的底层库。[C010]

```sources
S19 S12 S9 S8
```

## P16 · 波与量子:因果性进入 G

给弦加上惯性:$L=\frac{\partial^2}{\partial t^2}-c^2\nabla^2$。它的 G 有**两支**:

- **推迟格林函数**:响应只在源**之后**出现。敲一下,波纹向外扩,过去不受影响。
- **超前格林函数**:响应在源之前——数学上同样合法,物理上不采用。

"G 是一族函数"再加一条:同一个 L、同一边界,还可以选**因果约定**。[C012]

量子力学里,传播子 $\langle x'|e^{-iH(t-t')}|x\rangle$——"在 $x$ 放一个粒子,它在 $x'$ 出现的振幅"——
与薛定谔算符的 retarded Green 函数是**同一响应结构的不同表示**。
严格式要加两样东西:因果阶跃函数(只在 $t>t'$ 时非零)和约定因子(常见形式
$G^R(t,t')=-\frac{i}{\hbar}\Theta(t-t')\langle x'|U(t,t')|x\rangle$,系数随约定而变)。
所以不要写成"传播子就是 G"的等号;要说"同一结构、差一个约定外衣"。[C013]

量子场论把这套语言推到极致:理论围绕各种 G(传播子)组织。Strassler 有个好类比:
**G 之于波,如虚粒子之于实粒子**——G 是"中间量",把源和响应连起来,它自己不是可观测的波。

```sources
S2 S5 S11
```

## P17 · NEGF:量子器件的日常工具

把 P11 的傅里叶除法和 P08 的边界条件合起来,就是现代量子输运的引擎。

开放器件 = 中间一个小系统 + 左右两个电极(接触)。电子在接触间输运。

```visual
<svg viewBox="0 0 640 200" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <defs><marker id="arP17" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="oklch(0.68 0.15 55)"/></marker>
  <marker id="arP17b" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="oklch(0.68 0.15 55)"/></marker></defs>
  <rect x="40" y="60" width="120" height="80" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <text x="100" y="95" text-anchor="middle" fill="currentColor">左接触</text>
  <text x="100" y="115" text-anchor="middle" fill="var(--ink3)" font-size="11">化学势 μ_L</text>
  <rect x="480" y="60" width="120" height="80" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <text x="540" y="95" text-anchor="middle" fill="currentColor">右接触</text>
  <text x="540" y="115" text-anchor="middle" fill="var(--ink3)" font-size="11">化学势 μ_R</text>
  <rect x="240" y="52" width="160" height="96" rx="8" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
  <text x="320" y="92" text-anchor="middle" fill="currentColor">器件区 H</text>
  <text x="320" y="112" text-anchor="middle" fill="var(--ink3)" font-size="11">小系统(可原子级)</text>
  <path d="M 160 78 C 205 78 205 78 238 78" stroke="oklch(0.68 0.15 55)" stroke-width="2.2" fill="none" marker-end="url(#arP17)"/>
  <path d="M 164 122 C 205 122 205 122 234 122" stroke="oklch(0.68 0.15 55)" stroke-width="2.2" fill="none" marker-end="url(#arP17b)"/>
  <path d="M 478 78 C 440 78 440 78 404 78" stroke="oklch(0.68 0.15 55)" stroke-width="2.2" fill="none" marker-end="url(#arP17)"/>
  <path d="M 404 122 C 440 122 440 122 476 122" stroke="oklch(0.68 0.15 55)" stroke-width="2.2" fill="none" marker-end="url(#arP17b)"/>
  <text x="200" y="66" text-anchor="middle" fill="oklch(0.68 0.15 55)" font-size="12">Σ_L</text>
  <text x="200" y="140" text-anchor="middle" fill="oklch(0.68 0.15 55)" font-size="12">流入</text>
  <text x="440" y="66" text-anchor="middle" fill="oklch(0.68 0.15 55)" font-size="12">Σ_R</text>
  <text x="440" y="140" text-anchor="middle" fill="oklch(0.68 0.15 55)" font-size="12">流出</text>
  <text x="320" y="180" text-anchor="middle" fill="var(--ink3)" font-size="12">自能 Σ = 把"外面世界"焊进小系统的等效项(P08 边界条件的现代表示)</text>
</svg>
```

**NEGF(非平衡格林函数)方法**:

$$G^R(\omega)=\bigl[\omega+i\eta-H-\Sigma_L-\Sigma_R\bigr]^{-1}$$

| 符号 | 含义 |
|---|---|
| $H$ | 器件区哈密顿量(可以超大,原子级) |
| $\Sigma_{L,R}$ | 自能:把左右电极"焊"进来的等效项(边界条件的现代表示) |
| $G^R$ | 推迟格林函数:电子如何穿过器件 |
| $\eta$ | 无穷小虚部(P11 见过),保证收敛、选推迟支 |

极限自查(已解析验证,dossier V-05):$\Sigma\to0$ 时退回 $[\omega+i\eta-H]^{-1}$,
即 P11 的孤立情形。✓ [C014]

电流、密度、透射率全部从 $G^R$ 派生。**工业现状**:
Synopsys 的 QuantumATK 以 NEGF 为核心引擎做纳米器件电流仿真,
官方文档明确以 NEGF 计算非平衡电子密度。[C015]
P11 的"除法"在这里变成"带自能的矩阵求逆",但思想完全一样。

```sources
S4 S5 S6
```

## P18 · 什么时候不能用

四条硬边界,逐条给理由:

1. **非线性系统**:$L$ 依赖 $u$ 本身(大变形、接触、湍流)。
   叠加原理失效 → "查表相加"整条路断掉。格林函数是**线性**的产物。[C002]
2. **强关联多体**:电子互相作用的量子体系,G 依然存在,但 $\Sigma$ 无精确闭式,
   只能近似(GW、DMFT)。方法还是它,精度靠近似层。[C014]
3. **边界/介质复杂到无闭式**:层状、各向异性、不规则域——G 可能存在但没有可用公式。
   出路是 P19:数值构造它。
4. **时变系数**(方程里的参数随时间/位置变):平移对称破坏,P11 的除法失效。

**常见误用**(Tier E 高频卡点 [C016]):拿无穷域 G 硬套有界域问题;
推迟/超前支混用;忘记"一个 L 配一个边界条件才有唯一 G"。

> 只知道它能做什么,不算懂。知道它在哪里断掉,才算。

```sources
S10 S2 S5
```

## P19 · 数值化:没有闭式,就自己造一张表

工业问题几乎都有几何复杂性。三条主流路,全部是"造 G"的现代版:

1. **离散成矩阵,解稀疏方程**:有限元/有限差分 → $A\,x=b$。
   只解需要的列(单位源),不做整体求逆——P03 的表,稀疏版。
2. **边界元(BEM)**:G 已知时,把体积分搬到边界,只在**边界**离散。
   无限域问题(声辐射、电磁散射)的杀手锏。[C017]
3. **递归/分块**:NEGF 类问题按层递推(P17 的工业实现走这类算法)。

```callout Science → Engineering → Industry 链条(本 Lecture 的实例)
单位敲击响应(P01–P10)→ Kelvin/位错应力核(P14)→ TCAD 应力模块(P15)
→ Synopsys Sentaurus/QuantumATK 等工业求解器(P17)→ 45nm 以下晶体管的良率与性能(P15)
```

工程选择题:BEM 适合"线性 + 无限域 + 基本解已知";
FEM 适合"复杂材料 + 有限域";NEGF 适合"量子 + 开放"。
选择依据就是 P08/P18 讲的边界与线性条件。[C017,C023]

```sources
S13 S6
```

## P20 · 前沿(2023–2026)

经典理论(本 Lecture 的全部内容)已停止移动;前沿在三个方向:

- **神经算子**(2023–):学"源→响应"映射,绕开逐次求解。这条线里要分清两条不同的工作:
  **Laplace Neural Operator**(Cao et al.)已于 2024 年发表于 Nature Machine Intelligence,
  它基于 Laplace 域的极点-留数表示学习算子映射;而 **Green's Neural Operator with Neumann
  边界条件**是另一条更晚的研究线,目前还是预印本。两条线都还年轻,精度与可信度在建设中。[C018,C022]
- **关联体系的机器学习 G**(2025):用核方法(KRR)从平均场特征预测 1D Hubbard 模型的
  虚频自能,再经 Dyson 方程换回实频格林函数——替代昂贵的多体计算。已刊 J. Phys.: Condens.
  Matter;演示体系是一维,外推到真实材料仍是开放问题。[C024]
- **大规模 NEGF**(2024):rNEGF 用随机化方法把量子输运推到 **Hamiltonian 维度 4×10⁵**
  的体系(已刊 PRB;注意是矩阵维度,不是"百万原子")。[C019]

一条主线值得记住:**前沿没有推翻"单位敲击响应"这个结构,而是在让"造这张表"更便宜**——
用学习代替求解,用随机化代替精确逆。

```sources
S14 S20 S15 S7
```

## P21 · 我学会了吗?

以下五题覆盖 Recall / Concept / Transfer / Derivation / Application。
第 1、2 题建议先回 P09 拖一下滑块;第 5 题是开放设计题,答完对照解析要点。

```quiz
G(x,x′) 的定义里,"单位"指什么?
- 敲击的力是 1 牛顿,仅此而已
- [x] 源是一个单位点源:δ 函数,总量 1
- G 的数值最大是 1
?? 解析 [C001]:G 是 δ 点源的响应。第 3 项混淆了"单位"与"上限"——G 的峰值由系统决定,两端固定弦的 G 最大才 0.25。
```

```quiz
为什么 LG = δ 而不是 LG = 1?
- 约定俗成,没有原因
- 因为 G 定义在离散格点上
- [x] G 本身是"单位源产生的场",它满足的方程的右端就是那个单位点源
?? 解析 [C001]:把"在 x′ 敲单位一下,场仍满足方程"翻译成符号,右端自然是 δ。矩阵版 A g_j = e_j 说的同一件事。
```

```quiz
[Transfer] 半导体激光器的热仿真:芯片上一个纳米级热源,想知道整片芯片的温度分布。
这是格林函数问题吗?需要什么前提?
- [x] 是。若衬底近似均匀(平移不变的域),温度场 = 热源 ⊛ 热传导 G;还需指定散热边界
- 不是,热量问题没有 G
- 是,而且不需要边界条件
?? 解析 [C006,C007]:热方程与静电同构。卡点在于边界:P08 讲过,L+边界才唯一确定 G。芯片表面散热条件就是那个边界。
```

```quiz
[Derivation] 推导两端固定弦的 G 时,三步的顺序是?
- 先定斜率跳跃,再设直线,再贴边界
- [x] 先分段设直线(除源点外 G″=0)→ 两端贴零 → 源点处连续 + 斜率跳 1
- 先猜答案,再验证边界
?? 解析 [C004]:三步各自的依据:方程(直线)、边界(贴零)、δ 的强度(斜率跳跃)。把依据丢掉,记忆会散架。
```

```quiz
[Application · 开放题] SiGe 源/漏嵌入后,沟道下方某处产生了失配位错。
你要构造一个"应力响应格林函数"来评估位错对邻近晶体管的应力扰动。需要哪些要素?
?? 解析要点清单 [C010,C011]:
① 算符:线弹性 Navier 算符(衬底近似各向同性或取平均弹性常数);
② 源:位错的本征应变分布(P14 三步),即"单位错段"的等效力;
③ 边界:自由表面(应力为零)+ 可能的层间界面(失配跳跃,P08 的"边界决定 G");
④ 响应:应力张量场,G 现在是"单位错段 → 应力"的核(应力 G,见 Jin 2009);
⑤ 验证:量纲(Pa)、自由表面边界代入、远离位错时衰减行为;
⑥ 若几何太复杂无闭式:退到 P19 的数值表(稀疏解/BEM)。
答出 ①–⑤ 即算掌握;答出 ⑥ 属于超越本科的工程判断。
```

---

学完了。回到 P01 的那根弦:你现在知道,"敲一下记下来"这一个动作,
撑起了从库仑定律到位错应力、从滤波器到晶体管电流仿真的整座桥。

下次在任何领域遇到"响应∝源"的说法,先问三个问题:
**线性成立吗?边界是什么?单位源怎么定义?**——答案在手,你就已经有了它的格林函数。

```sources
S2 S4 S9 S10
```
