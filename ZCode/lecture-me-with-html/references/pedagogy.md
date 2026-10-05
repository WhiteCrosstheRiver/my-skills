# Pedagogy — Teaching Compiler 与页序设计

## Teaching Compiler(每个重要概念尽量走全)

```
WHY → CONCRETE PROBLEM → INTUITION → VISUAL MODEL → PATTERN
→ FORMAL DEFINITION → FORMULA → DERIVATION → WORKED EXAMPLE
→ GENERALIZATION → CONNECTION → APPLICATION → LIMITATION
```

禁止默认 Definition→Formula→Formula。定义永远晚于动机与直觉,除非主题本身就是形式对象。

## 开场三问(第 1 页必须回答前两问)

1. 这东西为什么被发明?
2. 没有它,什么问题解决不了?
3. 一个最小的具体问题是什么?(第 2 页的素材)

## 页 = 一个认知任务

一页只教一件事。典型页型:动机页 / 玩具问题页 / 图形直觉页 / 模式归纳页 /
定义页 / 符号解剖页 / 推导页(可拆多页) / 例题页 / 参数页(交互) /
推广页 / 连接页 / 领域应用页 / 限制页 / 前沿页 / 测验页。

## Prerequisite Capsule(前置胶囊)

前置知识可能缺失时,主线不绕路、不赶人,插入胶囊:

> 这里只需要知道:δ 函数有两个性质——① 处处为零除了一点;② 积分为 1。
> 够用了。想深挖,以后单独开一课。

胶囊只给"继续主线所需的最小知识",控制在 3–6 行。

## Example Ladder

toy → worked → scientific → engineering → industrial → research。
按主题适配,不强凑。每个梯级换一次语境,让用户看到同一结构在不同世界出现。

## Generalization 的三问

每次抽象(标量→矩阵→算符;离散→连续;1D→3D)必须回答:
什么变了?什么没变?核心结构是什么?

## Connection Map

相邻概念必须解释"为什么数学上或物理上相关",给同构/对应关系,
不许只列名字。一个概念至少连 2–4 个邻居。

## 限制与失效(固定模块)

假设清单 / 失效条件 / 只能近似使用的场景 / 常见误用。
只讲能做什么 = 不合格。

## Science → Engineering → Industry(固定模块)

构造具体链条:基本思想 → 科学用途 → 工程方法 → 软件/器件/工艺 → 产业应用。
禁止"广泛应用于工业"这种零信息句。

## Frontier(活跃主题固定模块)

近三年 review / emerging methods / open problems / ML 连接 / 新产业用途。
经典结论与最新研究分开陈述,时间敏感内容标年份。
