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
| Q8 | 工业落地(SiGe/TCAD/QuantumATK) | done | S6,S12 |
| Q9 | 2023–2026 前沿 | done | S7,S14,S15 |

## 2. Sources

### Tier A — 原始与权威
- **S1** [Cannell, George Green: Mathematician and Physicist 1793–1841](https://books.google.ba/books?id=x2Y2eb9IzwwC) — tier A — 1828 年论文史实、Thomson 推动再版
- **S2** [MIT OCW 18.303 Linear PDE (Fall 2014)](https://ocw.mit.edu/courses/18-303-linear-partial-differential-equations-fall-2014/) — tier A — G=L⁻¹、LG=δ、边界条件、各方程的 G
- **S3** [Strang, Delta functions and distributions (math.mit.edu)](https://math.mit.edu/~gs/) — tier A — δ 作为"最简右端"、脉冲响应观点
- **S4** [Datta, Nanoscale device modeling: the Green's function method (2000)](https://courses.ece.ucsb.edu/ECE194/194A_S13Banerjee/References/Datta_NEGF.pdf) — tier A — NEGF 概念基础
- **S5** [Camsari et al., The NEGF Method (arXiv:2008.01275)](https://arxiv.org/abs/2008.01275) — tier A(预印本) — NEGF 教学综述、接触与自能
- **S7** [Zhang et al., random NEGF for large-scale quantum transport, PRB 110, 155430 (2024)](https://link.aps.org/doi/10.1103/PhysRevB.110.155430) — tier A — 大规模 NEGF 前沿
- **S8** [Jin et al., New Green's function for stress field (2009), ScienceDirect](https://www.sciencedirect.com) — tier A — 点本征源应力 Green 函数
- **S9** [Pan & Chen, Green's Functions (Springer)](https://link.springer.com) — tier A — Kelvin/Mindlin/各向异性权威专著

### Tier B — 大学教学资料
- **S17** [MIT OCW 18.03 Differential Equations](https://ocw.mit.edu/courses/18-03-differential-equations-spring-2010/) — tier B — 脉冲响应与卷积单元
- **S18** [MIT OCW 18.03 notes: impulse response & convolution](https://ocw.mit.edu/courses/18-03-differential-equations-spring-2010/) — tier B — 权重函数观点

### Tier C — 优质直觉资源
- **S11** [Strassler, Virtual particles: what are they?](https://profmattstrassler.com/articles-and-posts/virtual-particles-what-are-they/) — tier C — "G 之于波,如虚粒子之于实粒子"

### Tier D — 工程与产业
- **S6** [QuantumATK NEGF Device 官方文档](https://docs.quantumatk.com/manual/NEGFDevice.html) — tier D — NEGF 器件仿真的工业实现
- **S12** [Stress mapping in strain-engineered Si pMOSFET (AIP 2012)](https://pubs.aip.org) — tier D — 应力工程应变硅产业与测量
- **S13** [ASME, Introduction to FEM/BEM methods, BEM fundamentals](https://asmedigitalcollection.asme.org) — tier D — BEM 以基本解为核、只在边界离散

### Tier E — 社区讨论
- **S10** [Physics SE: greens-functions 高赞问题集](https://physics.stackexchange.com/questions/tagged/greens-functions?tab=Votes) — tier E — 唯一性/边界条件/retarded vs advanced 卡点

### 其他
- **S14** [Laplace Neural Operator (arXiv 2023)](https://arxiv.org) — 预印本 — 神经算子学 Green 函数
- **S15** [ML Green's functions of strongly correlated systems (IOP)](https://iopscience.iop.org) — 预印本/期刊 — ML 预测自能与多体 G

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
| C001 | 线性算符 L 在指定(齐次)边界条件下,G 满足 L G = δ | definition | S2,S3,S10 | high | 线性;边界齐次 | P07,P08 |
| C002 | 线性系统:整体响应 = 各响应之和(叠加) | theorem | S2,S17 | high | 线性 | P04 |
| C003 | G 是 L 的逆(L⁻¹)的连续版;离散版 = 矩阵逆的列 | interpretation | S2,S3 | high | 可逆/唯一解 | P03,P09 |
| C004 | 两端固定单位弦,−d²G/dx²=δ 给出 G(x,x')=min(x,x')(1−max(x,x')) | theorem | S2,S18 | high | 1D;Dirichlet | P09 |
| C005 | L u = f 的解 u(x) = ∫ G(x,x') f(x') dx' | theorem | S2,S17 | high | 同 C001 | P10 |
| C006 | 平移不变域:G 只依赖差 → 卷积;傅里叶域 G(k)=1/L̂(k),如 1/k² | theorem | S2,S17 | high | 无限/周期域 | P11 |
| C007 | 静电:点电荷势 1/(4πε₀r) 是 −∇² 的 G;任意电荷分布 = 叠加 | application | S2,S3 | high | 真空中静电 | P13 |
| C008 | 弹性:Kelvin(1848)点力解 = 弹性算符的 G | historical/application | S9 | high | 无限各向同性体 | P14 |
| C009 | Mindlin(1936)给半空间内点力 G;Boussinesq(1885)表面点力 | historical | S9 | high | 半空间各向同性 | P14 |
| C010 | 位错/本征应变应力场 = 本征应变与应力 G 的卷积 | application | S8,S9 | high | 线弹性 | P14,SiGe |
| C011 | 嵌入 SiGe 源/漏压应变提升 pMOS 空穴迁移率;应变硅自 Intel 90nm 节点(约2002)起规模量产 | application | S12 | medium-high | 平面 MOSFET 时代 | P15 |
| C012 | 波方程有推迟/超前两支 G;推迟支编码因果(先源后响应) | theorem | S2,S5 | high | 线性波方程 | P16 |
| C013 | 量子传播子 ⟨x'|e^{-iHt}|x⟩ 是薛定谔算符的 G;QFT 里 G 即传播子 | interpretation | S4,S5,S11 | high | 量子力学 | P16 |
| C014 | 开放器件:G^R = [ω+iη−H−Σ_L−Σ_R]^{-1};NEGF 以 G 组织输运 | theorem | S4,S5,S6 | high | 单粒子/平均场级 | P17 |
| C015 | QuantumATK(Synopsys)以 NEGF 做纳米器件电流计算 | application | S6 | high | 工业软件 | P17 |
| C016 | 常见误区:不指明边界条件谈"G 唯一";推迟/超前混用;拿无穷域 G 硬套有界域 | interpretation | S10 | high | — | P08,P18 |
| C017 | BEM 以 G(基本解)为加权核,只需离散边界 | application | S13 | high | 线性、基本解已知 | P19 |
| C018 | 神经算子(FNO/LNO/Green's Neural Operator)学习 G;ML 预测关联体系自能 | frontier | S14,S15 | medium(快速演化) | 预印本身份 | P20 |
| C019 | rNEGF(2024)把 NEGF 推到大尺度器件 | frontier | S7 | high | 已刊 PRB | P20 |
| C020 | Green 1828 私人印发《论数学分析在电与磁理论中的应用》;Thomson 推动再版 | historical | S1 | high | — | P01 脚注 |

## 6. Formula Verification Log

| ID | 对象 | 验证项与方法 | 结果 |
|---|---|---|---|
| V-01 | C004 的 G | 折点斜率跳跃(node 实算):左 0.5,右 −0.5,跳跃 −1.000000 = δ 强度 | 通过 |
| V-02 | C005 特例 f≡1 | node 数值积分 ∫G(0.5,x')dx' = 0.125000,解析 x(1−x)/2|_{x=1/2}=0.125 | 通过 |
| V-03 | C003 的 2×2 例 | node:A=[[3,1],[1,2]],A·A⁻¹=I;x=A⁻¹(1,0)=(0.4,−0.2) | 通过 |
| V-04 | C001 量纲 | [G]·[L]=[u];δ 单位 1/长度 → G 带长量纲(1D 弦):一致 | 通过(解析) |
| V-05 | C014 极限 | Σ→0 且孤立:G^R→[ω+iη−H]^{-1},与 P11 一致 | 通过(解析) |

## 7. Open Questions

- 各向异性 SiGe 弹性常数的具体数值未查证 → P15 只讲结构与机制,不给具体 GPa 数值。
- S14 的准确 arXiv 编号未捕获 → 只写 arXiv 2023,标预印本。
