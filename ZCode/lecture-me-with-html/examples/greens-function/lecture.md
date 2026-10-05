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
S2: [MIT OCW 18.303 Linear PDE](https://ocw.mit.edu/courses/18-303-linear-partial-differential-equations-fall-2014/) — tier A — G=L⁻¹、LG=δ、边界条件
S3: [Strang, Delta functions and distributions](https://math.mit.edu/~gs/) — tier A — δ 与脉冲响应
S4: [Datta, Nanoscale device modeling: the Green's function method (2000)](https://courses.ece.ucsb.edu/ECE194/194A_S13Banerjee/References/Datta_NEGF.pdf) — tier A — NEGF 基础
S5: [Camsari et al., The NEGF Method (arXiv:2008.01275)](https://arxiv.org/abs/2008.01275) — tier A 预印本 — NEGF 教学综述
S6: [QuantumATK NEGF Device 官方文档](https://docs.quantumatk.com/manual/NEGFDevice.html) — tier D — 工业实现
S7: [Zhang et al., rNEGF, PRB 110, 155430 (2024)](https://link.aps.org/doi/10.1103/PhysRevB.110.155430) — tier A — 大规模 NEGF
S8: [Jin et al., New Green's function for stress field (2009)](https://www.sciencedirect.com) — tier A — 本征源应力 G
S9: [Pan & Chen, Green's Functions (Springer)](https://link.springer.com) — tier A — Kelvin/Mindlin 专著
S10: [Physics SE: greens-functions 高赞问题](https://physics.stackexchange.com/questions/tagged/greens-functions?tab=Votes) — tier E — 误区与卡点
S11: [Strassler, Virtual particles: what are they?](https://profmattstrassler.com/articles-and-posts/virtual-particles-what-are-they/) — tier C — 传播子直觉
S12: [Stress mapping in strain-engineered Si pMOSFET (AIP 2012)](https://pubs.aip.org) — tier D — 应力工程
S13: [ASME: Introduction to FEM/BEM, BEM fundamentals](https://asmedigitalcollection.asme.org) — tier D — 基本解方法
S14: [Laplace Neural Operator (arXiv 2023)](https://arxiv.org) — 预印本 — 神经算子
S15: [ML Green's functions of strongly correlated systems (IOP)](https://iopscience.iop.org) — 预印本 — ML 自能
S17: [MIT OCW 18.03 Differential Equations](https://ocw.mit.edu/courses/18-03-differential-equations-spring-2010/) — tier B — 脉冲响应与卷积
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
2. **量纲**:$G$ 的量纲 = 响应量纲 ÷ 力量纲。1D 弦里响应是长度、源是力,所以 $[G]=\mathrm{m/N}$。
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

同一个 $L=-\frac{d^2}{dx^2}$,换边界,得到不同的 G:

- 两端**固定**(弦):$G(0)=G(1)=0$
- 一端自由(杆):一端 $G=0$,另一端斜率为零
- **无限长**:没有边界,只要求 $|x|\to\infty$ 时衰减、且取"推迟"支(先因后果)

差异大到什么程度?无限长域的 $G$ 是一条直线段表达式,两端固定域是三角帆形(P09),
周期域又是另一副面孔。

```callout 立账本上一条高频误区 [C016]
"G 就是一条公式"是错的。正确说法:**L + 边界条件,共同唯一确定一个 G。**
Physics SE 高赞问题里,"为什么我的 G 和书上的不一样"的答案几乎都是:边界不同。
```

所以后面每讲一个领域的 G,第一句话都是:什么域、什么边界。[C016]

```sources
S2 S10
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

| 符号 | 含义 | 量纲(1D 弦) |
|---|---|---|
| $f(x')$ | 外部源(每单位长度受到的力) | N/m |
| $dx'$ | 一个微小源区域 | m |
| $G(x,x')\,dx'$ | 这个小区域贡献给 $x$ 的响应 | m |
| $u(x)$ | 全部小源响应的叠加 | m |

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

对 $L=-\frac{d^2}{dx^2}+m^2$:$\hat L(k)=k^2+m^2$,故 $\hat G(k)=\frac{1}{k^2+m^2}$。✓ 极限自查:$k\to\infty$ 时 $\hat G\to 0$——尖锐源的高频响应衰减,合理。[C006]

**为什么这一页重要**:凡是有平移对称的问题(均匀膜、无限栅格、自由空间),
"解微分方程"都退化成"做一个除法"。P17 的量子器件会再遇到它。

```sources
S2 S17
```

## P12 · 一个思想,四具身体

同一个数学结构,在不同学科里各有名字。不是比喻,是**同一个东西**:

| 名字 | 领域 | "敲一下"是什么 | "响应"是什么 |
|---|---|---|---|
| 矩阵逆的列 | 线性代数 | 单位向量 $e_j$ | 解向量 $x$ |
| 冲击响应 $h(t)$ | 信号/电路 | 单位电压脉冲 | 输出波形 |
| 格林函数 $G$ | 数学物理 | 单位点源 | 场分布 |
| 传播子 / 核 | 量子/统计 | 一点处的粒子 | 它跑到别处的振幅/概率 |

为什么必然同构?三个要件完全相同:**线性系统、单位刺激、叠加求和**。
凡满足这三件,背后自动是 $G$。

还有一串近亲:传递函数(控制)、感受率(susceptibility,统计物理)、影响系数(有限元)。
它们都是 $G$ 在各自方言里的叫法。学新领域时先问一句:**这里的"单位敲击"是什么?**常能一步到位。[C003,C013]

```sources
S3 S4 S17
```

## P13 · 静电学:你早就在用它

静电势满足 $-\nabla^2\phi=\rho/\varepsilon_0$。它的 $G$ 是:

$$G(\mathbf r,\mathbf r')=\frac{1}{4\pi|\mathbf r-\mathbf r'|}$$

代入 $u=\int Gf$:任意电荷分布的势 $=$ 每个点电荷的库仑势**求和**。
你从高中就会的"点电荷叠加",底层就是格林函数。[C007]

- **Formula anatomy(快版)**:$|\mathbf r-\mathbf r'|$ = 两点距离;$4\pi$ = 三维球面积分常数;
  $G$ 量纲 = 势/电荷;$\mathbf r'\to\mathbf r$ 时发散 = 点电荷自能发散(物理上用有限半径截断)。
- **极限自查**:$|\mathbf r|\to\infty$,$G\to 0$——离电荷越远势越弱。✓
- **镜像法**:接地平面旁的点电荷,$G$ = 真电荷 + 一个"假想镜像"的叠加。
  P08 说的"边界决定 G",这里是最著名的例子。

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
应变硅技术自 Intel 90nm 节点(约 2002)起进入规模量产,是"应变工程"的起点。[C011]

**力学链条**:

```
SiGe 晶格常数 > Si → 界面失配 → 沟道受压应变(迁移率↑)
→ 失配过大时产生失配位错(器件杀手)
→ 位错应力场 = 本征应变 ⊛ 应力 Green 函数(P14 的三步)
→ TCAD 工艺仿真用它预测应力分布与位错风险
```

其中"⊛"就是 $u=\int Gf$ 的弹性版。TCAD 工具预测"SiGe 体积分数多大、
嵌入多深会触发位错",核心部件之一就是这个卷积。
本页刻意不给 SiGe 弹性常数的具体数值(dossier open question:未查证),结构先立住。

科研延伸:各向异性、压电、双材料的 G 有闭式解析(Pan & Chen 专著),
是半导体力学仿真的底层库。[C010]

```sources
S12 S9 S8
```

## P16 · 波与量子:因果性进入 G

给弦加上惯性:$L=\frac{\partial^2}{\partial t^2}-c^2\nabla^2$。它的 G 有**两支**:

- **推迟格林函数**:响应只在源**之后**出现。敲一下,波纹向外扩,过去不受影响。
- **超前格林函数**:响应在源之前——数学上同样合法,物理上不采用。

"G 是一族函数"再加一条:同一个 L、同一边界,还可以选**因果约定**。[C012]

量子力学里,传播子 $\langle x'|e^{-iHt}|x\rangle$ 是薛定谔算符的 G:
"在 $x$ 放一个粒子,它在 $x'$ 出现的振幅"。量子场论里整个理论就是围绕各种 G
(传播子)组织的。Strassler 有个好类比:**G 之于波,如虚粒子之于实粒子**——
G 是"中间量",把源和响应连起来,它自己不是可观测的波。[C013]

```sources
S2 S5 S11
```

## P17 · NEGF:量子器件的日常工具

把 P11 的傅里叶除法和 P08 的边界条件合起来,就是现代量子输运的引擎。

开放器件 = 中间一个小系统 + 左右两个电极(接触)。电子在接触间输运。
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
选择依据就是 P08/P18 讲的边界与线性条件。[C017]

```sources
S13 S6
```

## P20 · 前沿(2023–2026)

经典理论(本 Lecture 的全部内容)已停止移动;前沿在三个方向:

- **神经算子学格林函数**(2023–):用 FNO/LNO 类网络直接学"源→响应"映射,
  目标是绕开逐次求解。Green's Neural Operator 已扩展到 Neumann 边界。
  注意:多为预印本,精度与可信度仍在建设中。[C018]
- **关联体系的机器学习 G**(2023–):用核方法/RNN 预测 Hubbard 模型的自能,
  替代昂贵的多体计算。[C018]
- **大规模 NEGF**(2024):rNEGF 用随机化方法把原子级量子输运推到百万原子尺度
  (已刊 PRB)。[C019]

一条主线值得记住:**前沿没有推翻"单位敲击响应"这个结构,而是在让"造这张表"更便宜**——
用学习代替求解,用随机化代替精确逆。

```sources
S14 S15 S7
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
