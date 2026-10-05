# Math Policy — LaTeX、验证与反瞬移

## 书写

- 源稿用 LaTeX:`$…$` 行内,`$$…$$` 独立成块(成块 = 居中展示)。
- 构建期由 KaTeX 服务端渲染(npm install katex),产物零数学 JS、完全离线。
- 允许:分数、根号、上下标、积分、求和、极限、矩阵(pm/bmatrix)、cases、aligned、
  希腊字母、偏导、\mathrm/\boldsymbol、\mathbb/\mathcal(基础集)。
  避免:\mathfrak 等冷僻字体(裁剪的字体集不含)。
- 渲染失败( KaTeX ParseError)会让构建报错并指出页码——照报错改 LaTeX。

## Formula Anatomy(首现公式必拆)

表格或列表逐项给出:每个符号含义 / 输入 / 输出 / 量纲 / 正负号意义 /
变量 vs 参数 / 隐含假设 / 参数增大趋势 / 极限行为。只给公式 = 不合格。

## 反数学瞬移

禁语(lint 拦截):显然可得、显然有、易得、经过简单计算、不难看出、
it is obvious、after some algebra、it can be shown。
每步推导必须回答:为什么?用了什么假设?物理/几何上意味着什么?
确需跳步(与学习目标无关的繁琐计算):明说"这里跳过一段纯代数,结果可在 S? 复核",
并给出来源。

## 验证清单(重要公式与例题,逐项过,记录进 dossier 验证日志)

1. dimensional analysis(量纲)
2. sign check(符号与物理直觉)
3. limiting case(参数 → 0/∞)
4. special case(对称/退化情形)
5. numerical sanity(用 node/python 实算一个点)
6. boundary-condition check(边界条件真的满足?)

示例(dossier 内):

```text
V-03 | G(x,x') = min(x,x')(1−max(x,x')) 满足 −G''=δ 且 G(0)=G(1)=0
     | 方法:node 数值求二阶差分 + 边界代入 | 通过
```

## STE 角色

ste-speech 只作 clarity layer:一句一事、短句、术语与符号稳定、少嵌套。
专业词照用,Simple language ≠ simple science。
一个符号一个含义:全文 `G` 不许一会儿是 Green 函数一会儿是剪切模量。
