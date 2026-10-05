# Research Dossier — 格林函数(Green's Function)

```yaml
topic: 格林函数(Green's function)
date: 2026-10-05
learner:
  math_level: undergraduate-basic
  physics_level: undergraduate-basic
  domain_level: semiconductor-research
lecture_file: lecture.md
```

## 0. Learner 档案与教学立场

- 高中数学好,大学数学学过不扎实:极限/积分可用,矩阵生疏 → 矩阵从 2×2 慢起,δ 函数用胶囊补。
- 懂基础物理:弹簧、弦、静电可以放心用。
- 半导体研究方向:S17(SiGe 应力)与 S5/S6(NEGF)讲到位,允许专业词。

## 1. Research Questions

| # | 问题 | 状态 | 来源 |
|---|---|---|---|
| Q1 | 历史动机:Green 为什么发明它 | done | S1 |
| Q2 | 最佳直觉讲法 | done | S10,S11 |
| Q3 | 权威定义与推导(线性算符/逆/δ/边界) | done | S2,S3 |
| Q4 | 经典具体化:静电/弹性/波/量子 | done | S2,S8,S9,S4 |
| Q5 | 卷积、傅里叶观点 | done | S2,S17 |
| Q6 | 数值化途径(BEM/稀疏逆) | done | S13 |
| Q7 | 常见误区 | done | S10 |
| Q8 | 工业落地(SiGe/TCAD/QuantumATK) | done | S6,S12,S19 |
| Q9 | 2023–2026 前沿 | done | S7,S14,S15,S20 |

## 2. Sources

> 定位纪律:每条来源给到文章/DOI/官方文档级;找不到精确地址的结论不进 Lecture。

### Tier A — 原始论文/专著/官方文档
- **S1** [Cannell, George Green: Mathematician and Physicist 1793–1841](https://books.google.ba/books?id=x2Y2eb9IzwwC) — 传记(Academic Press / Math. Gazette 1993)——1828 论文史实、Thomson 再版
- **S3** [Strang, When functions have no value(s): Delta functions and distributions (MIT, 论文)](https://math.mit.edu/~gs/) — δ 作为"最简右端"、脉冲响应观点
- **S4** [Datta, Nanoscale device modeling: the Green's function method (J. Phys.: Condens. Matter 12, R215, 2000)](https://courses.ece.ucsb.edu/ECE194/194A_S13Banerjee/References/Datta_NEGF.pdf) — NEGF 概念基础
- **S5** [Camsari, Faria, Sutton, Datta, The NEGF Method (arXiv:2008.01275, 预印本)](https://arxiv.org/abs/2008.01275) — NEGF 教学综述
- **S6** [QuantumATK NEGF Device 官方文档(Synopsys)](https://docs.quantumatk.com/manual/NEGFDevice.html) — 工业实现
- **S7** [Zhang, L. et al., Random NEGF method for large-scale quantum transport, Phys. Rev. B 110, 155430 (2024)](https://journals.aps.org/prb/abstract/10.1103/PhysRevB.110.155430) — 摘要明确 Hamiltonian 维度至 4×10⁵
- **S8** [Jin, Keer, Wang, New Green's function for stress field…, Int. J. Solids Struct. 46(21), 3788–3793 (2009)](https://www.sciencedirect.com/science/article/pii/S0020768309002698) — DOI 10.1016/j.ijsolstr.2009.07.015 —— 点本征源应力 G
- **S9** [Pan & Chen, Static Green's Functions in Anisotropic Media (Cambridge University Press, 2015)](https://www.cambridge.org/9781107034801) — Kelvin/Mindlin/各向异性权威专著
- **S12** [Krzeminski et al., Stress mapping in strain-engineered Si pMOSFET, J. Vac. Sci. Technol. B 30, 022203 (2012)](https://doi.org/10.1116/1.3683079) — 应力工程仿真 vs 实验对比
- **S14** [Cao, Kovachki, Azizzadenesheli et al., Laplace Neural Operator, Nat. Mach. Intell. 6, 631–640 (2024)](https://www.nature.com/articles/s42256-024-00844-4) — DOI 10.1038/s42256-024-00844-4 —— Laplace 域极点-留数表示的神经算子
- **S15** [Machine Learning Green's Functions of Strongly Correlated Hubbard Models, J. Phys.: Condens. Matter (2025)](https://iopscience.iop.org/article/10.1088/1361-648X/ae649b) — DOI 10.1088/1361-648X/ae649b —— KRR 学虚频自能;预印本 arXiv:2511.07252

### Tier B — 大学教学资料
- **S2** [MIT OCW 18.303 Linear PDE (Fall 2014)](https://ocw.mit.edu/courses/18-303-linear-partial-differential-equations-fall-2014/) — G=L⁻¹、LG=δ、边界条件;静态与含时 G 分开讲
- **S17** [MIT OCW 18.03 Differential Equations](https://ocw.mit.edu/courses/18-03-differential-equations-spring-2010/) — 脉冲响应与卷积单元
- **S18** [MIT OCW 18.03 notes: impulse response & convolution](https://ocw.mit.edu/courses/18-03-differential-equations-spring-2010/) — 权重函数观点

### Tier C — 优质直觉资源
- **S11** [Strassler, Virtual particles: what are they?](https://profmattstrassler.com/articles-and-posts/virtual-particles-what-are-they/) — "G 之于波,如虚粒子之于实粒子"

### Tier D — 工程与产业
- **S13** [ASME, Introduction to FEM/BEM methods, BEM fundamentals](https://asmedigitalcollection.asme.org) — BEM 以基本解为核、只在边界离散
- **S19** [Intel, Strained Silicon 背景材料(官方 pressroom)](https://www.intel.com/pressroom/kits/advancedtech/doodle/ref_strain/strain.htm) — 90nm 引入 strained silicon、PMOS embedded SiGe S/D

### Tier E — 社区讨论
- **S10** [Physics SE: greens-functions 高赞问题集](https://physics.stackexchange.com/questions/tagged/greens-functions?tab=Votes) — 唯一性/边界条件/retarded vs advanced 卡点

### 其他
- **S20** [Green's Neural Operator with Neumann boundary conditions (OpenReview)](https://openreview.net) — 预印本 —— 与 S14 不同的一条研究线

## 3. Concept Graph(页序依据)

```
        敲一下的响应(直觉)
              │
   线性+叠加 ─┼─ 单位冲击(离散:矩阵列)
              │            │
              │        A x = b → x = A⁻¹b
              ↓
   连续极限:δ 胶囊 → G(x,x')
              ↓
        L G = δ(定义自然出现)── 边界条件:G 是一族
              ↓
        u = ∫ G f(叠加公式)
        ┌─────┼──────────┐
   平移不变   连接图      数值化
   =卷积/傅里叶 (冲击响应/矩阵逆  (BEM/稀疏逆)
        │     /传播子)        │
        ↓                     ↓
  静电/弹性/波/量子/NEGF   工程→产业(TCAD/QuantumATK)
                                ↓
                          前沿(神经算子)
```

- 对象配色(跨页固定):源/力 = 橙,响应 = 蓝,单位冲击 δ = 黄,G = 深蓝。

## 4. Prerequisites

| 前置 | 判定 | 处理 |
|---|---|---|
| 线性与叠加 | 用户已会 | 正文直用 |
| 矩阵逆 | 生疏 | K1 胶囊(P02) |
| δ 函数 | 未学 | K2 胶囊(P05) |
| 傅里叶变换 | 学过不扎实 | K3 胶囊(P11) |
| 微分算子 | 基础可懂 | 正文一句话交代 |

## 5. Claim Ledger

| ID | Claim | Type | 来源 | 置信 | 假设 | 用于 |
|---|---|---|---|---|---|---|
| C001 | 线性算符 L 在指定(齐次)边界条件下,G 满足 L G = δ | definition | S2,S3,S10 | high | 线性;边界齐次 | P06,P07,P08,P21 |
| C002 | 线性系统:整体响应 = 各响应之和(叠加) | theorem | S2,S17 | high | 线性 | P04,P18 |
| C003 | G 是 L 的逆(L⁻¹)的连续版;离散版 = 矩阵逆的列 | interpretation | S2,S3 | high | 可逆/唯一解 | P03,P04,P12 |
| C004 | 两端固定单位弦,−d²G/dx²=δ 给出 G(x,x')=min(x,x')(1−max(x,x')) | theorem | S2,S18 | high | 1D;Dirichlet;归一化 T=1 | P06,P09,P21 |
| C005 | L u = f 的解 u(x) = ∫ G(x,x') f(x') dx' | theorem | S2,S17 | high | 同 C001 | P09,P10 |
| C006 | 平移不变域:G 只依赖差 → 卷积;傅里叶域 Ĝ(k)=1/L̂(k),如 1/k² | theorem | S2,S17 | high | 无限/周期域 | P11,P21 |
| C007 | 静电:算符 −∇² 的数学 G 是 1/(4πr);物理响应核(单位电荷的势)是 1/(4πε₀r);任意分布 = 叠加 | application | S2,S3 | high | 真空中静电;两核需区分 | P13,P21 |
| C008 | 弹性:Kelvin(1848)点力解 = 弹性算符的 G | historical/application | S9 | high | 无限各向同性体 | P14 |
| C009 | Mindlin(1936)给半空间内点力 G;Boussinesq(1885)表面点力 | historical | S9 | high | 半空间各向同性 | P14 |
| C010 | 位错/本征应变应力场 = 本征应变与应力 G 的卷积 | application | S8,S9 | high | 线弹性 | P14,P15,P21 |
| C011 | Intel 在 90nm 工艺代将 strained silicon 引入量产(PMOS embedded SiGe S/D);90nm 于 2003 年进入生产爬坡 | historical/application | S19 | high | 平面 MOSFET 时代 | P15,P21 |
| C012 | 含时波方程的 G 有推迟/超前两支;推迟支编码因果(先源后响应);因果选择属于含时问题,不属于静态 Laplace 型问题 | theorem | S2,S5 | high | 线性波方程 | P08,P16 |
| C013 | 量子传播子与薛定谔算符的 retarded G 是同一响应结构的不同表示;严格式含 Θ(t−t') 与 convention 因子(如 −i/ℏ) | interpretation | S4,S5,S11 | high | 单粒子量子力学 | P12,P16 |
| C014 | 开放器件:G^R = [ω+iη−H−Σ_L−Σ_R]^{-1};NEGF 以 G 组织输运 | theorem | S4,S5,S6 | high | 单粒子/平均场级 | P17,P18 |
| C015 | QuantumATK(Synopsys)以 NEGF 做纳米器件电流计算 | application | S6 | high | 工业软件 | P17 |
| C016 | 常见误区:不指明边界条件谈"G 唯一";推迟/超前混用;拿无穷域 G 硬套有界域 | interpretation | S10 | high | — | P08,P18 |
| C017 | BEM 以 G(基本解)为加权核,只需离散边界 | application | S13 | high | 线性、基本解已知 | P19 |
| C018 | Laplace Neural Operator(Cao et al.,Nat. Mach. Intell. 2024)用 Laplace 域极点-留数表示学习算子映射 | frontier | S14 | high(已刊) | — | P20 |
| C019 | rNEGF(2024,已刊 PRB)把 NEGF 推到 Hamiltonian 维度 4×10⁵ 的大规模体系 | frontier | S7 | high | 已刊 PRB | P20 |
| C020 | Green 1828 私人印发《论数学分析在电与磁理论中的应用》,提出单位源响应思想;后经 Thomson 推动再版 | historical | S1 | high | — | P01 |
| C021 | 静态 −d²/dx² 在整个实轴上的基本解 ∝ \|x−x'\|,随距离增长;无限域静态问题没有"衰减 G",需归一化/有限域处理 | theorem | S2,S18 | high | 1D 静态 | P08 |
| C022 | Green's Neural Operator with Neumann BC 是不同于 LNO 的另一条研究线(预印本) | frontier | S20 | medium | 预印本身份 | P20 |
| C023 | 工业 TCAD 应力模块主流靠连续介质数值求解(FEM/工艺仿真);解析/半解析 G 路线适用于线性几何的快速估计与校验 | interpretation | S12,S13 | medium | 厂商实现细节不完全公开 | P15,P19 |
| C024 | ML 学 G/自能:KRR 预测 1D Hubbard 虚频自能(2025,JPCM) | frontier | S15 | high(已刊) | 一维演示体系 | P20 |

## 6. Formula Verification Log

| ID | 对象 | 验证项与方法 | 结果 |
|---|---|---|---|
| V-01 | C004 的 G | 折点斜率跳跃(node 实算):左 0.5,右 −0.5,跳跃 −1.000000 = δ 强度 | 通过 |
| V-02 | C005 特例 f≡1 | node 数值积分 ∫G(0.5,x')dx' = 0.125000,解析 x(1−x)/2\|_{x=1/2}=0.125 | 通过 |
| V-03 | C003 的 2×2 例 | node:A=[[3,1],[1,2]],A·A⁻¹=I;x=A⁻¹(1,0)=(0.4,−0.2) | 通过 |
| V-04 | 量纲 | 初版按"真实单位"检查:**FAIL**(−u″=f 且 [u]=m 时 [f]=1/m,原写 N/m 自相矛盾)。改用归一化模型(T=1,约化单位)后:[f]=1/m,[G]=m,[G][f]=[u]=m ✓;物理版 −T u″=q([T]=N,[q]=N/m,[G]=m/N)在 P10 一句话备查 | 通过(修正后) |
| V-05 | C014 极限 | Σ→0 且孤立:G^R→[ω+iη−H]^{-1},与 P11 一致 | 通过(解析) |
| V-06 | C021 静态无限域 | 解 −G″=δ:G = \|x−x'\|/2 + 线性项;二阶差分 = δ,但 \|G\|\to∞ —— "衰减"不成立 | 通过(解析) |

## 7. Open Questions

- SiGe 各向异性弹性常数具体数值未查证 → P15 只讲结构与机制,不给具体 GPa 数值。
- TCAD 厂商(Coventor/Synopsys)应力模块是否内部使用 GF 核:厂商文档不公开 → C023 降为 medium,页面只说"解析路线 + 数值主流"两分法,不指名厂商实现。
