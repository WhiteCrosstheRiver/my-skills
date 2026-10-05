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

## P01 · 先别看任何方程:敲一下,会发生什么?

一根绷紧的弦,两端钉死。
你在中间用手指弹它一下,它成为一个形状:中间鼓起来,两端不动。

现在换一个问题。同样的弦,不弹一下,而是压上一个**任意的**重物——形状可以很复杂。
它的平衡形状怎么算?

朴素做法:对每个重物形状,重新解一遍力学方程。麻烦在于,重物有无数种。

更聪明的问法是:

- 先只研究**一种**最简单的扰动:在**一个点**上,敲**一下**(单位强度)。
- 把这个"单位敲击的响应"记录下来,记作一张表。
- 任意重物 = 无数个小敲击的排列组合。响应能不能直接**查表相加**?

这门 Lecture 的全部内容,就是把这张表讲清楚:它叫什么、怎么算、为什么合法、
在静电、弹簧、位错应力、晶体管里分别长什么样、什么时候失效。

> 历史注脚:George Green 在 1828 年私人印发了一本小册子《论数学分析在电与磁理论中的应用》,
> "单位源响应"的思想就在里面。这本册子当时只卖出约 50 份,后来靠 Kelvin 的推动才广为人知。[C020]

```sources
S1 S2
```

## P02 · 最简单的问题:两个弹簧

微分方程先放一边。看一个**离散**的、只有两个自由度的线性系统:两个耦合的弹簧块。

平衡方程写成矩阵形式 $A\,x = b$:

$$A=\begin{pmatrix}3 & 1\\ 1 & 2\end{pmatrix},\qquad x=\begin{pmatrix}x_1\\ x_2\end{pmatrix},\qquad b=\begin{pmatrix}b_1\\ b_2\end{pmatrix}$$

$b$ 是外力,$x$ 是位移。$A$ 描述弹簧网络:对角线是自己身上的弹簧刚度,非对角线是耦合。

```visual
<svg viewBox="0 0 640 130" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <line x1="40" y1="60" x2="120" y2="60" stroke="var(--ink3)" stroke-width="2"/>
  <rect x="120" y="40" width="46" height="40" rx="6" fill="oklch(0.80 0.09 92)" stroke="currentColor"/>
  <text x="143" y="65" text-anchor="middle" fill="currentColor">块1</text>
  <path d="M 166 60 q 10 -12 20 0 q 10 12 20 0 q 10 -12 20 0 q 10 12 20 0" fill="none" stroke="oklch(0.55 0.13 250)" stroke-width="2"/>
  <rect x="266" y="40" width="46" height="40" rx="6" fill="oklch(0.80 0.09 92)" stroke="currentColor"/>
  <text x="289" y="65" text-anchor="middle" fill="currentColor">块2</text>
  <line x1="312" y1="60" x2="392" y2="60" stroke="var(--ink3)" stroke-width="2"/>
  <text x="95" y="30" fill="var(--ink3)" font-size="11">墙</text>
  <text x="420" y="65" fill="currentColor">墙</text>
  <path d="M 143 14 L 143 34" stroke="oklch(0.68 0.15 55)" stroke-width="2.5" marker-end="url(#arP2a)"/>
  <defs><marker id="arP2a" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="oklch(0.68 0.15 55)"/></marker></defs>
  <text x="118" y="12" fill="oklch(0.68 0.15 55)" font-size="12">F₁(橙 = 源)</text>
  <text x="400" y="110" fill="var(--ink3)" font-size="12">右边的方程:每个块的受力平衡</text>
  <text x="400" y="96" fill="var(--ink3)" font-size="12">耦合:中间弹簧把两块连起来</text>
</svg>
```

图里每个部件对应 $A$ 的一个元素:对角线 = 各自挂在墙上的弹簧,非对角线 = 中间那根耦合弹簧。

```capsule K1 · 矩阵与逆,最少必要版
- 矩阵 $A$ 乘向量 = 一种"线性混合"。
- $A\,x=b$ 的意思是:已知混合规则 $A$ 和结果 $b$,反推原料 $x$。
- 反推的机器叫逆矩阵 $A^{-1}$:$x=A^{-1}b$。它满足 $A\,A^{-1}=I$。
- $I$ 是单位阵:乘谁都不改变谁。
```

本 Lecture 只需要这些。不熟也没关系,下面每一处用到,都会带着具体数字走。

```sources
S2
```

## P03 · 把"单位敲击"记下来:矩阵逆的真面目

分别只戳一个自由度,看系统的回应。

**戳第 1 块**($b=(1,0)$):解出 $x=(0.4,\,-0.2)$。
**戳第 2 块**($b=(0,1)$):解出 $x=(-0.2,\,0.6)$。

把两次响应并排摆好,拼成一个矩阵:

$$A^{-1}=\frac{1}{5}\begin{pmatrix}2 & -1\\ -1 & 3\end{pmatrix}$$

第一列就是"戳第 1 块的响应",第二列就是"戳第 2 块的响应"。
**矩阵逆不是抽象符号,它就是一张"单位敲击响应表"。**

```visual
<svg viewBox="0 0 640 210" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <text x="110" y="24" text-anchor="middle" fill="oklch(0.68 0.15 55)" font-size="12">戳块1(b₁=1)</text>
  <text x="110" y="40" text-anchor="middle" fill="var(--ink3)" font-size="11">响应 = A⁻¹ 第 1 列</text>
  <line x1="40" y1="150" x2="180" y2="150" stroke="currentColor" stroke-width="2"/>
  <circle cx="60" cy="150" r="7" fill="oklch(0.72 0.12 250)"/>
  <circle cx="110" cy="150" r="7" fill="oklch(0.72 0.12 250)"/>
  <path d="M 60 143 L 60 118" stroke="oklch(0.68 0.15 55)" stroke-width="2.5"/>
  <path d="M 110 143 L 110 156" stroke="oklch(0.72 0.12 250)" stroke-width="2.5"/>
  <text x="60" y="172" text-anchor="middle" fill="var(--ink3)" font-size="11">+0.4</text>
  <text x="110" y="176" text-anchor="middle" fill="var(--ink3)" font-size="11">−0.2</text>
  <text x="390" y="24" text-anchor="middle" fill="oklch(0.68 0.15 55)" font-size="12">戳块2(b₂=1)</text>
  <text x="390" y="40" text-anchor="middle" fill="var(--ink3)" font-size="11">响应 = A⁻¹ 第 2 列</text>
  <line x1="320" y1="150" x2="460" y2="150" stroke="currentColor" stroke-width="2"/>
  <circle cx="370" cy="150" r="7" fill="oklch(0.72 0.12 250)"/>
  <circle cx="420" cy="150" r="7" fill="oklch(0.72 0.12 250)"/>
  <path d="M 370 143 L 370 156" stroke="oklch(0.72 0.12 250)" stroke-width="2.5"/>
  <path d="M 420 143 L 420 118" stroke="oklch(0.68 0.15 55)" stroke-width="2.5"/>
  <text x="370" y="176" text-anchor="middle" fill="var(--ink3)" font-size="11">−0.2</text>
  <text x="420" y="172" text-anchor="middle" fill="var(--ink3)" font-size="11">+0.6</text>
  <text x="555" y="80" text-anchor="middle" fill="currentColor" font-size="12">并排放好 = A⁻¹</text>
  <path d="M 480 100 L 530 80" stroke="var(--ink3)" stroke-dasharray="4 3" fill="none"/>
  <text x="555" y="104" text-anchor="middle" fill="var(--ink3)" font-size="11">↑</text>
  <text x="555" y="118" text-anchor="middle" fill="var(--ink3)" font-size="11">响应表</text>
</svg>
```

图上的数字就是算出来的响应:橙箭头 = 你戳的位置(源,橙色),蓝 = 系统里各处的响应。
注意一个细节:戳块 1,块 2 会被**反向**拖动(−0.2)——中间弹簧被压缩,把块 2 往回顶。

自查(已实算,见 dossier V-03):$A\cdot A^{-1}=I$ 成立;
$b=(1,0)$ 时 $x=(0.4,-0.2)$,与上式一致。[C003]

一个像,一个坑:
- 像:这张表只依赖系统($A$),不依赖你之后想戳什么。存一次,到处用。
- 坑:若 $A$ 不可逆(比如某根弹簧没了,系统可以随便漂移),这张表不存在——
  "单位敲击响应"根本定义不下来。这不是数学洁癖,后面 P18 会回来。

```sources
S2 S3
```

## P04 · 任意源 = 一排单位敲击

还是那个系统。这次外力是 $b=(2,\,3)$。

关键观察:任何向量都能拆成单位向量的加权和:

$$\begin{pmatrix}2\\ 3\end{pmatrix}=2\begin{pmatrix}1\\ 0\end{pmatrix}+3\begin{pmatrix}0\\ 1\end{pmatrix}$$

因为系统是**线性**的,响应可以拆开算再合上:

$$x=A^{-1}\Big(2\,e_1+3\,e_2\Big)=2\,\underbrace{A^{-1}e_1}_{\text{戳第 1 块的响应}}+3\,\underbrace{A^{-1}e_2}_{\text{戳第 2 块的响应}}$$

**任意源的响应 = 单位敲击响应的加权和,权重就是源本身。**[C002,C003]

```visual
<svg viewBox="0 0 640 190" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <text x="100" y="26" text-anchor="middle" fill="oklch(0.68 0.15 55)" font-size="12">2 × 戳块1 的响应</text>
  <line x1="30" y1="150" x2="170" y2="150" stroke="currentColor" stroke-width="2"/>
  <path d="M 60 150 L 100 92 L 140 150" fill="none" stroke="oklch(0.72 0.12 250)" stroke-width="2.5"/>
  <text x="100" y="80" text-anchor="middle" fill="var(--ink3)" font-size="11">×2</text>
  <text x="215" y="130" fill="currentColor" font-size="18">+</text>
  <text x="330" y="26" text-anchor="middle" fill="oklch(0.68 0.15 55)" font-size="12">3 × 戳块2 的响应</text>
  <line x1="260" y1="150" x2="400" y2="150" stroke="currentColor" stroke-width="2"/>
  <path d="M 290 150 L 330 69 L 370 150" fill="none" stroke="oklch(0.72 0.12 250)" stroke-width="2.5"/>
  <text x="330" y="58" text-anchor="middle" fill="var(--ink3)" font-size="11">×3</text>
  <text x="440" y="130" fill="currentColor" font-size="18">=</text>
  <text x="545" y="26" text-anchor="middle" fill="oklch(0.68 0.15 55)" font-size="12">总响应 b=(2,3)</text>
  <line x1="470" y1="150" x2="620" y2="150" stroke="currentColor" stroke-width="2"/>
  <path d="M 500 150 L 545 46 L 590 150" fill="none" stroke="oklch(0.62 0.13 250)" stroke-width="3"/>
  <text x="545" y="170" text-anchor="middle" fill="var(--ink3)" font-size="11">两个响应图形直接相加</text>
</svg>
```

这就是"查表相加"合法的全部理由:线性。
非线性系统里这条路直接断掉——P18 会专门讲。

```sources
S2 S17
```

## P05 · 从两个自由度到一根连续的弦

现在把自由度从 2 个变成无穷多个:一根弦,每个位置 $x'$ 都可能被敲。

离散世界"戳第 $j$ 块"的单位力,在连续世界的对应物是什么?
是"只在一个点上、总量为 1 的力"。它无限窄,同时无限高,围出来的面积是 1。

```capsule K2 · δ 函数,最少必要版
δ(x−x') 只有两个性质,本 Lecture 只用这两个:
1. 筛选:除了 x = x' 一点,处处为零。
2. 归一:积分为 1,$\int \delta(x-x')\,dx' = 1$。
推论(筛选性质):$\int \delta(x-x')\,f(x')\,dx' = f(x)$。
```

于是离散的"第 $j$ 列响应表"升级为连续的**二元函数**:

```visual
<svg viewBox="0 0 640 200" style="color:var(--ink);font-family:var(--sans)" font-size="12">
  <text x="320" y="20" text-anchor="middle" fill="var(--ink3)">把"一个点的单位力"逐步推到极限:宽度→0,高度→∞,面积恒等于 1</text>
  <line x1="30" y1="165" x2="190" y2="165" stroke="currentColor"/>
  <rect x="88" y="90" width="44" height="75" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
  <text x="110" y="186" text-anchor="middle" fill="var(--ink3)">宽 w</text>
  <text x="110" y="80" text-anchor="middle" fill="var(--ink3)">高 1/w</text>
  <line x1="230" y1="165" x2="390" y2="165" stroke="currentColor"/>
  <rect x="296" y="45" width="28" height="120" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
  <text x="310" y="186" text-anchor="middle" fill="var(--ink3)">更窄</text>
  <line x1="450" y1="165" x2="610" y2="165" stroke="currentColor"/>
  <path d="M 528 165 L 530 22 L 532 165 Z" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
  <text x="530" y="186" text-anchor="middle" fill="var(--ink3)">→ δ(x−x′)</text>
  <text x="320" y="40" text-anchor="middle" fill="oklch(0.68 0.13 92)" font-size="13">面积 = 宽 × 高 = 1(黄色,恒定)</text>
</svg>
```


$$\underbrace{G(x,\,x')}_{\text{在 }x'\text{ 敲一下,}x\text{ 处的响应}}$$

单位冲击 δ 用黄色标记,源用橙色,响应用蓝色——全文不变,看到颜色就知道角色。

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

```sources
S2 S3
```

## P07 · 现在,LG = δ 才自然出现

$G$ 是"单位源产生的响应"。**响应场必须仍然满足这个系统的方程**——
只是这次的源,恰好是一个单位点源,也就是 δ。

写成方程(以弦为例,算符 $L=-\frac{d^2}{dx^2}$):

$$L\,G(x,x')=\delta(x-x')$$

这一行不再莫名其妙,它只是把一句话翻译成符号:

> **在 $x'$ 敲单位一下,得到的形状,依然满足弦的方程。**

```visual
<svg viewBox="0 0 640 150" style="color:var(--ink);font-family:var(--sans)" font-size="13">
  <defs><marker id="arP7" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="var(--ink3)"/></marker></defs>
  <rect x="40" y="45" width="140" height="52" rx="8" fill="oklch(0.85 0.12 92)" stroke="oklch(0.68 0.13 92)"/>
  <text x="110" y="68" text-anchor="middle" fill="currentColor">单位点源</text>
  <text x="110" y="86" text-anchor="middle" fill="var(--ink3)" font-size="11">δ(x − x′)(黄色)</text>
  <rect x="250" y="45" width="140" height="52" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <text x="320" y="68" text-anchor="middle" fill="currentColor">系统 L</text>
  <text x="320" y="86" text-anchor="middle" fill="var(--ink3)" font-size="11">弦:−d²/dx² + 边界</text>
  <rect x="460" y="45" width="140" height="52" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <text x="530" y="68" text-anchor="middle" fill="currentColor">响应形状 G</text>
  <text x="530" y="86" text-anchor="middle" fill="var(--ink3)" font-size="11">蓝:三角形帆(P09)</text>
  <line x1="180" y1="71" x2="244" y2="71" stroke="var(--ink3)" stroke-width="1.6" marker-end="url(#arP7)"/>
  <line x1="390" y1="71" x2="454" y2="71" stroke="var(--ink3)" stroke-width="1.6" marker-end="url(#arP7)"/>
  <text x="212" y="60" text-anchor="middle" fill="var(--ink3)" font-size="11">喂进去</text>
  <text x="422" y="60" text-anchor="middle" fill="var(--ink3)" font-size="11">吐出来</text>
  <text x="320" y="128" text-anchor="middle" fill="var(--ink3)" font-size="12">这张"流水线证"就是 LG = δ:输出恰好是 G 的名字</text>
</svg>
```

离散对照一模一样:$A\,g_j=e_j$(第 $j$ 列)。连续版只是把"列"换成"$x'$"。

```capsule K-小 · 微分算符,一句话
$L=-\frac{d^2}{dx^2}$ 读作"把函数微分两次再变号"。它对形状做的事:
鼓包越尖,作用越猛。$L\,G=\delta$ 就是"尖峰输入"对应的"输出形状"。
```

注意"指定边界条件下"六个字:方程只定了半个 G,另外一半由边界定。下一页专门讲。[C001]

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

四个性质,逐条对应你已见过的东西:

1. 源加倍 → 响应加倍($G$ 不变)。
2. 源移动 → $G$ 的三角帆整体平移(在平移不变的域里,P11)。
3. 两个源 → 两个响应相加(P09 的交互演示过)。
4. $f=\delta(x-x_0)$ 代回去 → $u(x)=G(x,x_0)$。**定义自动被公式包含。** [C005]

一句话:这个积分就是"查表相加"的连续版。$G$ 是表,$f$ 是权重,$u$ 是总和。

```sources
S2 S17
```

## P11 · 平移不变的世界:卷积与傅里叶

无限长的弦(没有钉死的端点)有一条新对称性:整体平移,系统不变。
于是 $G$ 只依赖**差**:$G(x,x')=G(x-x')$。积分变成**卷积**:

$$u(x)=\int G(x-x')\,f(x')\,dx'$$

```capsule K3 · 傅里叶变换,最少必要版
把函数看成不同波长正弦波的叠加。
傅里叶变换 = 换一组坐标:从"每个位置的值"换成"每个波长的振幅"。
它有一条 magic:微分变乘法($\partial_x \to ik$),卷积变乘法。
```

magic 用到 $L\,G=\delta$ 上:微分变乘法,δ 变常数 1,于是

$$\hat G(k)=\frac{1}{\hat L(k)}$$

```visual
<svg viewBox="0 0 640 190" style="color:var(--ink);font-family:var(--sans)" font-size="12">
  <text x="140" y="24" text-anchor="middle" fill="currentColor" font-size="13">实空间:卷积(麻烦)</text>
  <text x="500" y="24" text-anchor="middle" fill="currentColor" font-size="13">傅里叶空间:乘法(省事)</text>
  <rect x="50" y="40" width="180" height="60" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <text x="140" y="66" text-anchor="middle" fill="currentColor">u = G ⊛ f</text>
  <text x="140" y="86" text-anchor="middle" fill="var(--ink3)" font-size="11">逐点扫过整个域</text>
  <rect x="410" y="40" width="180" height="60" rx="8" fill="var(--blue-bg)" stroke="var(--blue)"/>
  <text x="500" y="66" text-anchor="middle" fill="currentColor">Û(k) = Ĝ(k) · f̂(k)</text>
  <text x="500" y="86" text-anchor="middle" fill="var(--ink3)" font-size="11">每个 k 一次除法</text>
  <path d="M 230 70 L 300 70" stroke="var(--ink3)" stroke-width="1.6" marker-end="url(#arF1)"/>
  <path d="M 410 100 L 340 100" stroke="var(--ink3)" stroke-width="1.6" stroke-dasharray="4 3" marker-end="url(#arF1)"/>
  <defs><marker id="arF1" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="var(--ink3)"/></marker></defs>
  <text x="265" y="60" text-anchor="middle" fill="oklch(0.62 0.13 250)" font-size="11">傅里叶变换</text>
  <text x="375" y="116" text-anchor="middle" fill="var(--ink3)" font-size="11">反变换回来</text>
  <line x1="60" y1="140" x2="180" y2="140" stroke="currentColor"/>
  <path d="M 60 138 L 90 120 L 120 138 L 150 114 L 180 132" fill="none" stroke="oklch(0.72 0.12 250)" stroke-width="2"/>
  <text x="120" y="158" text-anchor="middle" fill="var(--ink3)" font-size="11">锯齿状叠加</text>
  <line x1="430" y1="140" x2="560" y2="140" stroke="currentColor"/>
  <circle cx="475" cy="128" r="4" fill="oklch(0.72 0.12 250)"/><circle cx="500" cy="121" r="4" fill="oklch(0.72 0.12 250)"/><circle cx="525" cy="128" r="4" fill="oklch(0.72 0.12 250)"/>
  <text x="495" y="158" text-anchor="middle" fill="var(--ink3)" font-size="11">几个独立的数</text>
  <text x="320" y="182" text-anchor="middle" fill="var(--ink3)">对称性把"解方程"降级成"做除法"</text>
</svg>
```

对 $L=-\frac{d^2}{dx^2}+m^2$:$\hat L(k)=k^2+m^2$,故 $\hat G(k)=\frac{1}{k^2+m^2}$。✓ 极限自查:$k\to\infty$ 时 $\hat G\to 0$——尖锐源的高频响应衰减,合理。[C006]

**为什么这一页重要**:凡是有平移对称的问题(均匀膜、无限栅格、自由空间),
"解微分方程"都退化成"做一个除法"。P17 的量子器件会再遇到它。

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
