#!/usr/bin/env python3
"""Incremental-update helper: what changed in the project since the last stamp?

usage: python check.py [--dir <.explainer folder>] [--stamp]

Reads <dir>/sources.json (hand-written: which files feed which sections) and
<dir>/fingerprints.json (written by --stamp after a successful update). Prints
changed/new/missing sources, the sections they feed, the first new line of
append-only logs, new files in watched folders, and extracts to re-run.
Same file formats as check.ps1, so either script can be used.
"""
import datetime, hashlib, json, pathlib, sys

def fp(p):
    b = p.read_bytes()
    return {"size": len(b), "lines": b.count(b"\n"), "sha256": hashlib.sha256(b).hexdigest()}

def main():
    a = sys.argv[1:]
    d = pathlib.Path(a[a.index("--dir") + 1] if "--dir" in a else pathlib.Path(__file__).parent).resolve()
    cfg = json.loads((d / "sources.json").read_text(encoding="utf-8"))
    root = (d / cfg["project_root"]).resolve()
    fpp = d / "fingerprints.json"
    old = json.loads(fpp.read_text(encoding="utf-8")) if fpp.exists() else {"files": {}, "watch_seen": {}}
    print("last stamp:", old.get("stamped", "never"))
    files, sections, changed = {}, set(), set()
    print("\n== sources ==")
    for s in cfg["sources"]:
        p, feeds = root / s["path"], ",".join(s["feeds"])
        if not p.exists():
            print(f"MISSING   {s['path']}  [{feeds}]"); continue
        cur = files[s["path"]] = fp(p); prev = old["files"].get(s["path"])
        if prev and prev["sha256"] == cur["sha256"]:
            continue
        changed.add(s["path"]); sections.update(s["feeds"])
        if not prev:
            print(f"NEW       {s['path']}  [{feeds}]")
        elif s.get("kind") == "append" and cur["size"] > prev["size"]:
            print(f"APPENDED  {s['path']}  [{feeds}]  read from line {prev['lines'] + 1} (+{cur['lines'] - prev['lines']} lines)")
        else:
            print(f"CHANGED   {s['path']}  [{feeds}]  {prev['size']} -> {cur['size']} bytes")
    seen = {}
    if cfg.get("watch"):
        print("\n== watched folders ==")
        for w in cfg["watch"]:
            key = w["dir"] + "|" + w["pattern"]
            wd = root / w["dir"]
            names = sorted(x.name for x in wd.glob(w["pattern"]) if x.is_file()) if wd.exists() else []
            seen[key] = names
            for n in names:
                if n not in old["watch_seen"].get(key, []):
                    print(f"NEW FILE  {w['dir']}/{n}  [{','.join(w['feeds'])}]"); sections.update(w["feeds"])
    if cfg.get("extracts"):
        print("\n== extracts to re-run ==")
        for x in cfg["extracts"]:
            hit = [i for i in x["inputs"] if i in changed]
            if hit:
                print(f"RE-RUN    {x['script']}  (input changed: {', '.join(hit)})  -> {x['output']}")
    print("\n== sections to revisit ==")
    print(", ".join(sorted(sections)) if sections else "none: the explainer is up to date with its sources")
    if "--stamp" in a:
        out = {"stamped": datetime.datetime.now().isoformat(timespec="seconds"), "files": files, "watch_seen": seen}
        fpp.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\nstamped {len(files)} files -> fingerprints.json")

if __name__ == "__main__":
    main()
