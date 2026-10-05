# am.mjs 本地补丁说明

本目录的 `am.mjs` 相比上游 QingYunA/answer-me-with-html v0.4.7 多了一个 `mathify()` 公式排版补丁(2026-10-05):

- 内联 code 里的公式自动排版:`x^2`、`t^(3/2)`、`x^{n+1}` → 真上标;`E_n`、`x_(ij)` → 真下标;希腊字母单词(`pi`/`omega`/`Sigma`)→ 字形;`sqrt(` → √;变量斜体衬线(Cambria Math/Georgia 回退)。
- 公式单独成段 → 居中虚线框块(`.am-math-display`,nowrap + 横滚)。
- sup/sub 里的 ASCII `-` 自动换为数学减号 U+2212(斜体数学字体下 ASCII 连字符不可见)。
- 普通命令(`pip install` 等)不受影响;门控正则判定。

钩子位置:`emit()`(页面与视频共用的唯一写盘点),CSS 注入在 `</head>` 前。

## 回归测试

渲染混合用例(`^(-1)`、一段双公式夹散文、长公式、纯命令),检查:

1. `grep 'am-math-display">[^<]*</code>'` 必须为 0(display 块不得跨段吞标签);
2. `<sup>−1</sup>` 含 U+2212;
3. 截图目测负号可见、无孤字折行。

## 更新后重打

`am update` / `npx skills update` 会覆盖补丁。重打步骤:备份新 am.mjs,在 `emit()` 的 `writeFileSync5(file, result.html)` 改为 `mathify(result.html)`,在 `function emit` 前插入 mathify 函数(见 git 历史中本文件的版本)。
