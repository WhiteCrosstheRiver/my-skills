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

| 命令 | 用途 |
|---|---|
| `doctor` | 检查本机连接、权限、版本，不打印凭据 |
| `deep-search --topic "领域" --query "扩展检索式" --years 2018-2026 --limit 100` | 多源检索与引文扩展；默认含 Google Scholar / X-MOL 宿主协作源（ResearchGate 需 `--providers researchgate` 显式开启，登录墙繁琐不建议）（生成 `web_sources.json` 检索链接，宿主读取后经 `--input` 合并）；选择策略宁全勿缺，间接相关默认保留 |
| `resume --run PATH --input FILE [--input FILE2]` | 把宿主采集的 Scholar BibTeX、ResearchGate RIS、X-MOL/网页采集的 DOI/Markdown 列表合并进候选池（Crossref 校验 DOI，自动去重） |
| `resume --run PATH --selection selection.json` | 按已有任务继续入库和整理证据 |
| `note-template --run PATH --paper ID` | 创建待分析模板；不是完成的笔记 |
| `publish-note --run PATH --paper ID` | 校验并发布宿主完成的详细笔记 |
| `dedup --collection KEY --apply` | 仅合并标识及元数据兼容的重复组；省略 apply 仅生成计划 |
| `distill --collection KEY` | 蒸馏整个收藏夹树，无篇数截断；原笔记及历史版本保留 |
| `review --title "领域综述" --source-run PATH` | 冻结已发布精读，生成比较矩阵供宿主综合 |
| `review --publish --run PATH` | 发布独立审查通过的综述、离线HTML与完整证据包 |
| `resume --run PATH --retry-errors` | 根据任务类型恢复；不会将等待人工分析当成已完成 |

全局 `--output` / `--url` 位于命令前。收藏夹参数为 Zotero key，CLI错误信息会说明缺失范围。`distill --topic` 是短语匹配；语义领域筛选由宿主扩展并整理收藏夹。深度检索支持 Scholar BibTeX、ResearchGate RIS、X-MOL/网页采集的 DOI/Markdown 列表，使用 `--input FILE`。

收藏夹布局：专题收藏夹默认嵌套在「我的文献 → Agent」父收藏夹下（`--parent-collection-name`，默认 `Agent`，传空字符串则在根层创建），不会打乱你手工设计的收藏夹树。

导入规则：库中已有同一文献（DOI/arXiv/标题匹配）时复用该条目，只补全空缺的元数据字段（DOI、年份、摘要、URL、期刊、作者）并下载缺失的 PDF，**绝不覆盖**用户已有的任何字段、笔记与附件；库中没有时新增条目——新条目位于「我的文献」根层并额外加入主题收藏夹。

综述保留参考长篇HTML的章节逻辑、逐章引证和证据矩阵；视觉参考 [Apple Support](https://support.apple.com/)，采用白底、清晰层级和蓝色导航。KaTeX随包分发，离线不访问CDN。请复制整个版本目录或解压 Zotero 的离线ZIP，再打开 `review.html`，不要只复制单个HTML文件。

修改文件会生成新版本；用户手工修改的便条、Markdown、PDF和快照不覆盖。无损合并仅将重复父条目送入回收站。原生事务结果不明时要求重启Zotero后恢复，不能靠重复发送写请求猜测是否成功。

## 测试

```powershell
python -m pytest -q
# 以下会在明确命名的测试收藏夹创建合成测试条目
$env:ZOTERO_SKILLS_LIVE = "1"
python -m pytest -q
```

真实研究示例、个人文献库信息、下载PDF和运行凭据不进入仓库。自动化校验能验证引用位置与内容存在，论点是否确实被证据支持仍由助手独立核查。

真实验收摘要保存在 `tests/acceptance-stage*.md`。测试会保留标记 TEST 的合成记录，不永久删除数据。首次四阶段测试环境为 Windows / Python 3.13 / Zotero 10.0.3 / Zotero Agent 2.2.2；原生合并接口在其他 Zotero 版本应重新验收。

KaTeX 0.16.22 的版权和许可证位于 `scripts/zotero_skills/assets/katex/LICENSE`；其包完整性按官方 npm SHA512 核对。
