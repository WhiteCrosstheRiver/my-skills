# Codex skills

- [cost-aware-delegation](cost-aware-delegation/SKILL.md)：按任务难度和可验收性选择子智能体。
- [computer-use-delegate](cu-delegate/skill/computer-use-delegate/SKILL.md)：Codex 写任务书并验收，本机 ZCode GLM 负责网页观察与操作。当前为 v0.1 experimental；原生桌面自动委派尚未联通。

## 安装 computer-use-delegate

在已安装 ZCode 并登录 Coding Plan 的 Windows 机器上，从仓库根目录运行：

```powershell
python ./Codex/cu-delegate/scripts/install.py
```

安装两个 skill：`~/.codex/skills/computer-use-delegate` 和
`~/.zcode/skills/gui-operator`。已安装且需要更新时，检查修改后加 `--update`。
新主机浏览器依赖准备方法见
[local-runtime.md](cu-delegate/skill/computer-use-delegate/references/local-runtime.md)。

在新的 Codex 对话中使用 `$computer-use-delegate`。只安装 Codex 端入口不足以启动
ZCode worker；还需 ZCode 端的 gui-operator 及本机运行环境。

[完整说明](cu-delegate/README.md) · [训练验收记录](cu-delegate/scorecards/v0.1.md)

完整训练包保留原有路径，便于复跑安装、契约测试和 L1 原型测试。版本清单按文件
原始字节计算 SHA-256；包内 `.gitattributes` 关闭换行归一化，保持检查点哈希。
验收记录包含已测结果与限制；浏览器保留输入的 9/9 不代表完整桌面能力或节费指标通过。
