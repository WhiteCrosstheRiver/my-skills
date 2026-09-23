# Zotero Skills

供 Codex / Claude Code 调用的 Zotero 研究技能及 Python CLI。模型负责学术阅读和写作，程序负责检索、入库、证据管理、无损合并与版本化输出。

## 安装

需要 Python 3.11+、正在运行的 Zotero，以及启用 Write Operations 和 Run JavaScript 的 Zotero Agent。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./zotero-skills[test]"
.\.venv\Scripts\python.exe ./zotero-skills/scripts/zotero_cli.py doctor
```

把 `zotero-skills` 文件夹安装/链接到 `~/.codex/skills/` 或 `~/.claude/skills/`。在助手中说：“使用 zotero-skills 深度检索机器学习原子势，逐篇生成详细笔记。”

令牌通过本机现有配置或 `ZOTERO_MCP_TOKEN` 读取；不要提交令牌。输出默认保存于 `~/Documents/ZoteroSkills`，可用 `ZOTERO_SKILLS_OUTPUT` 或命令前的 `--output` 改变。

## 工作方式

`deep-search` 保存候选文献，助手审核相关性后用 `resume --selection` 导入并提取全文。助手逐篇编写 `note.md` 与 `claims.json`，最后运行 `publish-note`。程序不会把空白模板或抓取到的摘要冒充完整精读。

每篇保存 Zotero 子便条、Markdown 附件、本地Markdown及证据定位。没有全文时明确区分摘要/元数据级分析。技术细节和模式说明见 [SKILL.md](SKILL.md) 与其中的参考文件。

## 测试

```powershell
python -m pytest -q
# 以下会在明确命名的测试收藏夹创建合成测试条目
$env:ZOTERO_SKILLS_LIVE = "1"
python -m pytest tests/test_live.py -q
```

真实研究示例、个人文献库信息、下载PDF和运行凭据不进入仓库。自动化校验能验证引用位置与内容存在，论点是否确实被证据支持仍由助手独立核查。
