# Visualization Policy — 视觉推理,不是插图

## 最高判据

> 把所有 Notes 隐藏,只播放 visual + 一句旁白,用户还能不能复述主线?
> 能,才算 3B1B;不能,就还是插图。

## 3B1B-like = Persistence + Transformation + Prediction + Emergence + Minimalism

1. **Persistence(持久对象)**:同一教学链里的对象跨页/跨拍保持身份——不重画、
   不改名、不换色。用 `data-obj="source|response|delta|kernel|system"` 标注;
   页头 `{objects=a,b inherits=Pxx}` 声明延续关系,lint 检查。
2. **Transformation(变换对应)**:数学操作必须有视觉对应——
   源加倍→响应加倍;源平移→核平移;两源→响应相加;求导→斜率/尖峰出现。
3. **Prediction(先猜再看)**:关键变化前用 ```predict``` 让用户猜
   (不是考试,是激活大脑);每个核心链至少 3 处。
4. **Emergence(公式长出来)**:公式不空降;前几拍把公式的每一项画在图上,
   公式出现时用户在图里能逐项认出。每个重要公式标 formula origin。
5. **Minimalism(当拍无关即淡出)**:当前拍用不到的对象降透明度或不在场;
   一拍只加一个元素。

## Scene → Beat

- 页面单位之上是拍:`→` 先推拍,拍尽翻页。
- 一个 scene = 一个认知动作的分解,3–7 拍;旁白一句 ≤30 字,写在 `<bN>…</bN>`。
- 三个语义动作就够:appear(新信息进场)、move(同一对象变化)、transform(同一概念
  换表示)。数据属性:`data-beat="N"` 分组,`data-fx="grow|slide|fade"` 定变换。

## Visual Object Registry(dossier 必填)

```yaml
visual_objects:
  source:   { color: 橙, symbol: f/δ,  position: 左/输入 }
  system:   { color: 灰, symbol: L/A,  position: 中 }
  response: { color: 蓝, symbol: u,    position: 右/输出 }
  delta:    { color: 金, symbol: δ,    position: 源的位置 }
  kernel:   { color: 深蓝, symbol: G,  position: 响应结构 }
```

跨页颜色/位置语义不变:从弹簧到静电到 NEGF,语法都是"橙源 → 灰系统 → 蓝响应"。

## Visual Storyboard(写稿前的正式阶段)

| Scene | Question | Persistent objects | Beat change | Formula born | Prediction |
|---|---|---|---|---|---|
| S01 | 一次敲击能告诉我们什么? | string, source, response | move source | — | yes |

先设计分镜,再写正文。禁止先写文章再找地方插图。

## 页面模式

- `theater`:大视觉 + 一句旁白;首屏正文 ≤120 中文字;严谨内容进 ```notes```。
- `derive`:图与公式同步推导(视觉证明页);公式逐拍出现。
- `read`:纸面正文(历史/产业/背景/表格密集页)。
- `lab`:参数交互(回答"参数变了会怎样")。
- 核心概念形成期(通常 P01–P11)以 theater/derive 为主;应用与前沿页可以 read 为主。

## 按知识形状选型(保留)

| 知识形状 | 图形 |
|---|---|
| 谁连向谁、因果 | flow / concept map |
| 历史 | timeline;数序 | number line |
| 函数关系 | function plot;场 | field response |
| 演化 | before/after、parameter sweep;结构 | layered diagram、matrix viz |
| 权衡 | comparison |

实现:静态结构用 ```visual```(SVG);逐拍推理用 ```scene```;参数交互用 ```lab```。
每张图 caption 回答"帮用户理解什么",答不出就删。
