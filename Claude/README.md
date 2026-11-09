# Claude skills

Claude 桌面应用（Code 标签页 / Claude Code）使用的 skill。每个 skill 一个子目录，内含 `SKILL.md`。

## 安装

把 skill 目录复制到 `~/.claude/skills/<skill-name>/`（Windows：`%USERPROFILE%\.claude\skills\`），新会话即可使用。

## Skills

- [project-explainer-3b1b](project-explainer-3b1b/SKILL.md)：把科研项目的台账、日志、数据和图整理成一个可分享的多语言（中/英，可扩展）HTML 讲解页，3Blue1Brown 风格：矢量图表、KaTeX 公式、交互物理动画。构建素材保存在项目内隐藏的 `.explainer/` 文件夹，进度更新时用 `check` 只找出变化的来源和受影响的章节，做增量修改，不必整页重写。
