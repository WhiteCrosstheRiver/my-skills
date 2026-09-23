from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import write_lock_path
from .core import MCP, Network, Run, default_output, lock, read_json
from .search import discover, prepare_selected
from .notes import note_template, publish


def parser():
    p = argparse.ArgumentParser(description="Zotero Skills: evidence-grounded research workflows")
    p.add_argument("--output", type=Path, default=default_output(), help="Private workspace, outside the skill repository")
    p.add_argument("--url", help="Zotero Agent MCP URL (token via local configuration/environment)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    search = sub.add_parser("deep-search", help="Discover candidates; selection and analysis are performed by the host agent")
    search.add_argument("--topic", required=True)
    search.add_argument("--query", action="append", dest="queries")
    search.add_argument("--providers", nargs="+", choices=["semantic", "crossref", "arxiv", "europepmc", "openalex"], default=["semantic", "crossref", "arxiv"])
    search.add_argument("--years")
    search.add_argument("--limit", type=int, default=100)
    search.add_argument("--candidate-limit", type=int, default=100)
    search.add_argument("--citation-hops", type=int, choices=[0, 1], default=1)
    search.add_argument("--input", action="append", dest="inputs", default=[])
    search.add_argument("--library", type=int, default=1)
    search.add_argument("--collection")
    search.add_argument("--collection-name")
    resume = sub.add_parser("resume")
    resume.add_argument("--run", type=Path, required=True)
    resume.add_argument("--selection", type=Path)
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
    for module in ["dedup", "distill", "review"]:
        try:
            mod = __import__("zotero_skills." + module, fromlist=["register"])
        except ModuleNotFoundError as exc:
            if exc.name != "zotero_skills." + module:
                raise
        else:
            mod.register(sub)
    return p


def execute(args):
    if args.command == "doctor":
        return MCP(args.url).doctor()
    if args.command == "status":
        return Run(args.run).state
    if args.command == "deep-search":
        if args.limit < 1 or args.candidate_limit < 1:
            raise ValueError("Limits must be positive")
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
                if args.discover:
                    return discover(run, net)
                with lock(write_lock_path()):
                    return prepare_selected(run, MCP(args.url), net, args.selection)
            mod = __import__("zotero_skills." + run.state["mode"], fromlist=["resume"])
            return mod.resume(run, args)
    mod = __import__("zotero_skills." + args.command, fromlist=["execute"])
    return mod.execute(args)


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
