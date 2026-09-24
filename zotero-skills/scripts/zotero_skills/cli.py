from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .core import write_lock_path
from .core import MCP, Network, Run, default_output, lock, read_json
from .search import discover, import_input_files, prepare_selected
from .notes import note_template, publish


def parser():
    p = argparse.ArgumentParser(description="Zotero Skills: evidence-grounded research workflows")
    p.add_argument("--output", type=Path, default=default_output(), help="Private workspace, outside the skill repository")
    p.add_argument("--url", help="Zotero Agent MCP URL (token via local configuration/environment)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("help", help="Show a table of every command and what it does")
    sub.add_parser("update", help="Update this skill from its remote git repository")
    search = sub.add_parser("deep-search", help="Discover candidates; selection and analysis are performed by the host agent")
    search.add_argument("--topic", required=True)
    search.add_argument("--query", action="append", dest="queries")
    search.add_argument("--providers", nargs="+", choices=["semantic", "crossref", "arxiv", "europepmc", "openalex", "scholar", "researchgate", "xmol"], default=["semantic", "crossref", "arxiv", "scholar", "xmol"], help="scholar/researchgate/xmol are host-assisted: search URLs are emitted to web_sources.json, never scraped")
    search.add_argument("--years", help="Inclusive range with a hyphen, e.g. 2018-2026")
    search.add_argument("--limit", type=int, default=100)
    search.add_argument("--candidate-limit", type=int, default=100)
    search.add_argument("--citation-hops", type=int, choices=[0, 1], default=1)
    search.add_argument("--input", action="append", dest="inputs", default=[])
    search.add_argument("--library", type=int, default=1)
    search.add_argument("--collection")
    search.add_argument("--collection-name")
    search.add_argument("--parent-collection-name", default="Agent", help="Topic collections nest under this parent collection (default Agent); pass empty string to create at library root")
    resume = sub.add_parser("resume")
    resume.add_argument("--run", type=Path, required=True)
    resume.add_argument("--selection", type=Path)
    resume.add_argument("--input", action="append", dest="inputs", default=[], help="Merge host-collected .bib/.ris/.md export files into the candidate pool first")
    resume.add_argument("--discover", action="store_true")
    resume.add_argument("--retry-errors", action="store_true")
    resume.add_argument("--restore", action="store_true", help="Restore prepared, unmerged dedup children")
    for name in ["publish-note", "note-template"]:
        command = sub.add_parser(name)
        command.add_argument("--run", type=Path, required=True)
        command.add_argument("--paper", required=True)
    status = sub.add_parser("status")
    status.add_argument("--run", type=Path, required=True)
    # Later-stage modules register their interfaces without changing shared behavior.
    for module in ["dedup", "distill", "review", "download"]:
        try:
            mod = __import__("zotero_skills." + module, fromlist=["register"])
        except ModuleNotFoundError as exc:
            if exc.name != "zotero_skills." + module:
                raise
        else:
            mod.register(sub)
    return p


def execute(args):
    if args.command == "help":
        return help_table()
    if args.command == "update":
        return update_from_remote()
    if args.command == "doctor":
        result = MCP(args.url).doctor()
        from .search import probe_sources
        result["sources"] = probe_sources(Network(args.output / "cache"))
        return result
    if args.command == "status":
        return Run(args.run).state
    if args.command == "deep-search":
        if args.limit < 1 or args.candidate_limit < 1:
            raise ValueError("Limits must be positive")
        if args.years:
            # Accept 2018:2026 or 2018-2026; provider adapters require the hyphen form.
            args.years = re.sub(r"[;:~至]", "-", args.years)
        config = {k: v for k, v in vars(args).items() if k not in ["output", "url", "command"]}
        run = Run.create(args.output, "deep-search", config)
        with lock(run.path / ".lock"):
            return discover(run, Network(args.output / "cache"))
    if args.command == "note-template":
        run = Run(args.run)
        paper = next(p for p in run.state["papers"] if p["id"] == args.paper)
        directory = run.paper_dir(paper)
        target = directory / "note.md"
        if target.exists():
            raise ValueError("note.md exists; refusing to overwrite")
        target.write_text(note_template(read_json(directory / "evidence.json")), encoding="utf-8")
        return {"draft": str(target), "status": "draft_not_published"}
    if args.command == "publish-note":
        run = Run(args.run)
        with lock(run.path / ".lock"), lock(write_lock_path()):
            return publish(run, args.paper, MCP(args.url))
    if args.command == "resume":
        run = Run(args.run)
        with lock(run.path / ".lock"):
            if args.restore and run.state['mode'] != 'dedup':
                raise ValueError('--restore applies only to a dedup recovery manifest')
            if run.state["mode"] == "deep-search":
                net = Network(args.output / "cache")
                if args.inputs:
                    with lock(write_lock_path()):
                        added = import_input_files(run, net, args.inputs)
                    if not args.discover and not args.selection:
                        return {"run": str(run.path), "merged_inputs": added, "candidates": len(run.state["candidates"]), **({"next": "All input files were already merged."} if not added else {"next": "Open any remaining web_sources.json urls, then write selection.json with included [{id, reason}] and resume --selection FILE."})}
                if args.discover:
                    return discover(run, net)
                with lock(write_lock_path()):
                    return prepare_selected(run, MCP(args.url), net, args.selection)
            mod = __import__("zotero_skills." + run.state["mode"], fromlist=["resume"])
            return mod.resume(run, args)
    module = "download" if args.command == "fetch-pdfs" else args.command
    mod = __import__("zotero_skills." + module, fromlist=["execute"])
    return mod.execute(args)


def help_table():
    return {
        "overview": "模型负责学术阅读与写作，本 CLI 负责确定性操作：检索、入库、证据管理、无损合并与版本化输出。全局 --output / --url 放在命令最前面。",
        "commands": [
            ["doctor", "检查 Zotero 连接/权限/版本，并探测全部检索源(含 scholar/xmol 等)连通性"],
            ["help", "显示本命令表"],
            ["update", "从远程 GitHub 仓库拉取并更新本 skill"],
            ["deep-search --topic 主题 --query 检索式 --years 2018-2026", "多源深度检索+引文扩展；默认含 Google Scholar/X-MOL 宿主协作源(生成 web_sources.json，宿主浏览器读取后 --input 合并)；候选宁全勿缺"],
            ["resume --run PATH --input FILE", "把宿主采集的 BibTeX/RIS/DOI列表 合并进候选池(Crossref 校验，幂等)"],
            ["resume --run PATH --selection selection.json", "按入选清单导入 Zotero(已有条目只补空缺，绝不覆盖；新条目入 我的文献/Agent/专题)"],
            ["resume --run PATH --discover", "重试失败的检索(保留已缓存结果)"],
            ["resume --run PATH --retry-errors", "按任务类型恢复出错文献"],
            ["status --run PATH", "查看任务 pending/error/published 状态"],
            ["note-template --run PATH --paper ID", "生成待分析笔记模板(草稿，非成品)"],
            ["publish-note --run PATH --paper ID", "校验并发布宿主完成的笔记(note.md+claims.json)到 Zotero"],
            ["dedup --collection KEY [--apply]", "去重：仅合并标识/元数据兼容的重复组，保留子条目与恢复清单；省略 apply 仅出计划"],
            ["fetch-pdfs --run PATH [--force]", "为已选文献补缺PDF：OpenAlex/Unpaywall/Semantic/arXiv 多解析器合法回退，只增不覆盖，可断点续跑"],
            ["distill --collection KEY", "蒸馏整个收藏夹树(无篇数截断)，复用笔记管线，保留历史版本"],
            ["review --title 标题 --source-run PATH", "冻结已发布精读，生成证据矩阵供宿主综合写综述"],
            ["review --publish --run PATH", "发布版本化综述、离线HTML(内置KaTeX)与完整证据包"],
        ],
        "typical_flow": "deep-search → 宿主读 web_sources.json 合并 --input → 写 selection.json → resume --selection → 逐篇读证据写 note.md/claims.json → publish-note → (可选) distill / review",
        "docs": "各阶段详见 references/{search,notes,dedup,distill,review}.md",
    }


def update_from_remote():
    import subprocess
    skill_root = Path(__file__).resolve()
    while skill_root != skill_root.parent and not (skill_root / ".git").exists():
        skill_root = skill_root.parent
    if not (skill_root / ".git").exists():
        raise ValueError("Skill folder is not inside a git checkout; reinstall with pip install -e <folder> or git clone")
    result = subprocess.run(["git", "-C", str(skill_root), "pull", "--ff-only"], capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError("git pull failed: " + (result.stderr or result.stdout).strip()[:300])
    head = subprocess.run(["git", "-C", str(skill_root), "log", "-1", "--format=%h %s"], capture_output=True, text=True, timeout=30)
    return {"skill_root": str(skill_root), "status": "updated" if "Already up to date" not in result.stdout else "already-up-to-date", "git_output": result.stdout.strip()[:300], "head": head.stdout.strip()}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    try:
        result = execute(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    except Exception as exc:
        # Provider request URLs may contain tokens; never dump traceback/request headers.
        message = str(exc)
        import re
        message = re.sub(r"(?i)(api_key|token|key)=([^\s&'\"]+)", r"\1=[REDACTED]", message)
        print(json.dumps({"error": type(exc).__name__, "message": message}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
