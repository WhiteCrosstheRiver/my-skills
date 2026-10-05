# Visualization Policy — 每张图必须解决一个认知问题

## 按知识形状选型

| 知识形状 | 图形 |
|---|---|
| 谁连向谁、因果 | flow / concept map |
| 历史与阶段 | timeline |
| 数的大小与序 | number line / bar |
| 函数关系 | function plot(坐标系统) |
| 场与响应 | field response(1D 曲线族/2D 色场) |
| 状态演化 | before/after、parameter sweep |
| 结构组成 | layered diagram、matrix visualization |
| 权衡 | comparison 表+图 |
| 能量地形 | energy landscape |

实现:SVG 手绘(静态结构)或 ```lab``` 块内 canvas(参数交互)。
Mermaid 不可用(构建器不处理),需要流程图就画 SVG。

## 判据

每张图写一句 caption 回答:**这张图帮用户理解什么?**答不出,删图。
装饰性插图、与正文重复的图、信息密度低于两行文字的图,一律不要。

## 3B1B 的四个教学动作(可执行版)

1. **Progressive reveal**:新元素逐页进入。第 n 页画的图,第 n+1 页沿用并只加一层。
2. **Visual continuity**:同一对象跨页保持同名、同色、同位置逻辑、同符号。
   在 dossier 的 concept graph 里为每个主要对象固定颜色(如:源=橙,响应=蓝,δ=黄)。
3. **Formula emergence**:最终公式不凭空出现;前几页的图就是公式的每一项,
   公式页开头先复现图形模式,再给出符号化。
4. **Transformation 对应**:数学操作与可视变化一一对应
   (源加倍→响应加倍;源平移→核平移;两源→响应叠加)。

## 交互纪律

交互只回答一个问题:"改变参数会怎样?"
好例:拖动 source 位置看响应场实时变;改变 damping 看 impulse response。
坏例:定义页塞滑块;为了"高级感"加 3D。
每个 ```lab``` 块顶部必须有一句"你在看什么 + 拖动 X 会怎样"。
