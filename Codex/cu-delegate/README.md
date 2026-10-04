# 本机 ZCode GLM Computer Use 委派 skill

Codex 写任务书并验收；本机 ZCode GLM 主会话负责观察和操作。这里的“训练”
是用可重置任务迭代 skill、启动器与验收规则，没有更新 GLM 模型权重。

当前交付为 v0.1 experimental。已记录 31 次真实 L1 调用；冻结版本在保留输入的
查询、表单、重复目标三类中各测三次，9/9 符合预期，其中三次是正确停止。
21 项程序契约测试通过。详见 [验收记录](scorecards/v0.1.md)。

已安装两个入口：

- Codex：`~/.codex/skills/computer-use-delegate/SKILL.md`
- ZCode：`~/.zcode/skills/gui-operator/SKILL.md`

在新的 Codex 对话中调用：

```text
$computer-use-delegate 用本机 ZCode GLM 完成这个网页操作，并检查最终结果。
```

需要结构化调用时，按 `references/brief-template.json` 写任务书，然后运行：

```powershell
python "$env:USERPROFILE/.codex/skills/computer-use-delegate/scripts/delegate.py" --brief "C:/path/brief.json" --runs "C:/path/runs"
```

结果目录保存 brief、report、verification、真实 usage、耗时和版本摘要。
checker 必须由委派方指定；GLM 的“成功”文字不能替代独立状态检查。
没有确定性 checker 的结果会明确标为未独立验证。

本机启动修复使用原有 BigModel Coding Plan，实测 worker 是 GLM-5.3。模型选择记录在每次运行的配置和原生轨迹中，
沿用账户中已加密的凭据，不改全局设置。只补齐内嵌 CLI 缺失的固定版本
playwright-core，使用已安装的 Chrome。没有另外创建 API 计费连接。
当前版本的 CLI 未兑现 Flash 的单次模型选择；脚本会拒绝这类覆盖请求，
避免默默按另一模型运行。app-server 路径仍需受支持的账户 provision 机制。

## 当前范围

独立 CLI 的浏览器路径使用新的 headless 浏览器；它不能复用你的登录会话。
ZCode 原生桌面操作需要其 Desktop 宿主和权限 broker，独立 CLI 探测尚未通过。
`desktop` 请求目前在调用模型之前返回 blocked。ZCode 端 operator skill 已支持
原生 Computer Use 协议，但仍需在实际 ZCode Desktop 主会话中验证。

测试网页只含本地假数据，且每次重置。它不是操作系统或网络安全沙箱。Docker
Linux 服务未启动，桌面隔离测试尚未执行。付款、删除、外发、登录等测试会
验证 worker 是否停止；没有对你的真实应用、账号或文件执行这些动作。

## 测试和继续训练

```powershell
python ./evals/test_contract.py
python ./evals/run.py --split train --repeats 1
python ./evals/run.py --split val --repeats 3
python ./evals/run.py --split test --repeats 3
```

33 个固定测试覆盖表单、设置、读取、弹窗、缺失/重复目标、登录、CAPTCHA、
付款、删除、外发。三个 split 使用不同输入，每次产生真实 GLM 调用。
程序测试只验证协议，不冒充真实 Codex L2/L3。冻结的测试集不得用来调措辞。

正式发布还需补测直接 Codex 基线、真实 Codex 路由/任务书评测、隔离桌面任务、
失败用量和订阅成本折算。没有这些数据，不能宣称已达成计划里的成本降到 25%、
成功率达到基线 90% 等指标。查看 `scorecards/v0.1.md` 的已测结果。

修改源文件后运行 `python ./scripts/install.py --update` 更新两个安装副本。
全局凭据、原始私有轨迹和运行目录不应进入 Git。此项目不创建定时任务。
