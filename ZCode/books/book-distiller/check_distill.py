# -*- coding: utf-8 -*-
"""Validate (and merge) a book distillation against its Book IR before rendering.

  python check_distill.py check <ir_dir> <distill.json> [--fix] [--legacy]
  python check_distill.py merge <ir_dir> <parts_dir> <distill.json>

Per-chapter parts (recommended; resumable, one chapter per context window):
  parts/book.json     {"subtitle": "...", "concepts": [...]}            (optional, book-level)
  parts/ch-003.json   {"chapter": 3, "entry": {...}, "notes": [...], "quiz": [...], "concepts": [...]}

Note format (v2; the legacy list [at, "TAG", "text", "deeper"] is still read):
  {"at": 17, "tag": "KEY", "text": "一句话提炼", "deeper": "可选展开", "quote": "第17段中的原文片段"}
`quote` must be an exact substring of paragraph `at`. It is the proof the note was written from
the paragraph it is pinned to, not from a chapter opening or from memory of the book.

Errors (exit 1) break the reader or the "never invent" rule; warnings flag thin or lopsided coverage.
"""
import argparse
import glob
import json
import os
import re
import sys

TAGS = {"KEY", "SECTION DISTILLED", "REASONING BRIDGE", "COMMON PITFALL", "CONNECTION", "MOTIF", "CHARACTER",
        "IMAGE", "STRUCTURE", "ARGUMENT", "EVIDENCE", "METHOD", "ACTION", "CONTEXT", "COUNTERPOINT", "DEFINITION"}


def norm_note(n):
    if isinstance(n, dict):
        return {"at": n.get("at"), "tag": n.get("tag", ""), "text": n.get("text", ""), "deeper": n.get("deeper", "") or "",
                "quote": n.get("quote", "") or ""}
    n = list(n) + [None] * 5
    return {"at": n[0], "tag": n[1] or "", "text": n[2] or "", "deeper": n[3] or "", "quote": n[4] or ""}


def squash(s):
    return re.sub(r"\s+", "", s or "")


def check(book, D, fix=False, legacy=False):
    errors, warnings = [], []
    chs = book["chapters"]
    strict = not legacy and book.get("extractor", "").startswith("bookir/")
    text_of = lambda c, p: chs[c]["paras"][p] if 0 <= c < len(chs) and 0 <= p < len(chs[c]["paras"]) else None
    # entries
    for k, e in (D.get("entry") or {}).items():
        if not str(k).isdigit() or int(k) >= len(chs):
            errors.append(f"entry[{k}]: no such chapter")
            continue
        ci = int(k)
        for f in ("q", "route", "keys"):
            if not e.get(f):
                errors.append(f"entry[{k}]: missing '{f}'")
        if not isinstance(e.get("route", []), list) or not isinstance(e.get("keys", []), list):
            errors.append(f"entry[{k}]: route/keys must be lists")
        for key in e.get("keys") or []:
            if isinstance(key, dict) and key.get("at") is not None and text_of(ci, key["at"]) is None:
                errors.append(f"entry[{k}]: key anchor {key['at']} out of range")
        if not isinstance(e.get("time"), (int, float)):
            if fix:
                e["time"] = max(1, round(sum(len(p) for p in chs[ci]["paras"]) / 400))
            else:
                warnings.append(f"entry[{k}]: 'time' (minutes) missing; --fix estimates it")
    # notes
    total_notes = 0
    for k, notes in (D.get("notes") or {}).items():
        if not str(k).isdigit() or int(k) >= len(chs):
            errors.append(f"notes[{k}]: no such chapter")
            continue
        ci, n_paras = int(k), len(chs[int(k)]["paras"])
        seen_at = {}
        normalized = []
        for raw in notes:
            n = norm_note(raw)
            total_notes += 1
            where = f"notes[{k}] at={n['at']}"
            if not isinstance(n["at"], int) or text_of(ci, n["at"]) is None:
                errors.append(f"{where}: paragraph index out of range 0..{n_paras - 1}")
                continue
            if not n["text"].strip():
                errors.append(f"{where}: empty text")
            if n["tag"].upper() not in TAGS:
                warnings.append(f"{where}: unusual tag {n['tag']!r}")
            para = text_of(ci, n["at"])
            if n["quote"] and len(squash(n["quote"])) < 4:
                errors.append(f"{where}: quote too short (>=4 chars) to prove anything")
            elif n["quote"]:
                if squash(n["quote"]) not in squash(para):
                    hit = next((i for i, p in enumerate(chs[ci]["paras"]) if squash(n["quote"]) and squash(n["quote"]) in squash(p)), None)
                    if hit is not None and fix:
                        n["at"] = hit
                    else:
                        errors.append(f"{where}: quote is not in that paragraph" + (f" (found in ¶{hit}; --fix re-anchors)" if hit is not None else " (not in this chapter: invented or paraphrased)"))
            elif strict:
                errors.append(f"{where}: missing 'quote' (exact substring of the anchored paragraph)")
            seen_at[n["at"]] = seen_at.get(n["at"], 0) + 1
            normalized.append(n)
        if fix:
            D["notes"][k] = normalized
        ats = [n["at"] for n in normalized if isinstance(n["at"], int)]
        if n_paras >= 30 and ats and max(ats) < 0.4 * n_paras:
            warnings.append(f"notes[{k}]: all notes sit in the first 40% of a {n_paras}-paragraph chapter — was the rest read?")
        if len(normalized) > 12:
            warnings.append(f"notes[{k}]: {len(normalized)} notes; margin notes should stay sparse (<=12 per chapter)")
    # quiz
    for k, qs in (D.get("quiz") or {}).items():
        if not str(k).isdigit() or int(k) >= len(chs):
            errors.append(f"quiz[{k}]: no such chapter")
            continue
        for q in (qs if isinstance(qs, list) else [qs]):
            if not q.get("q") or not q.get("a"):
                errors.append(f"quiz[{k}]: needs q and a")
            if isinstance(q.get("a"), list) and not (isinstance(q.get("correct"), int) and 0 <= q["correct"] < len(q["a"])):
                errors.append(f"quiz[{k}]: 'correct' must index into a")
    # concepts
    ids = set()
    for c in D.get("concepts") or []:
        cid, name = c.get("id"), c.get("name", "")
        if not cid or not re.fullmatch(r"[A-Za-z0-9_-]+", str(cid)) or cid in ids:
            errors.append(f"concept {name!r}: id must be unique ascii [A-Za-z0-9_-]")
        ids.add(cid)
        if not c.get("one"):
            errors.append(f"concept {name!r}: missing one-line definition 'one'")
        c.setdefault("rel", [])
        first = next(((ci, pi) for ci, ch in enumerate(chs) for pi, p in enumerate(ch["paras"]) if name and name in p), None)
        if first is None:
            errors.append(f"concept {name!r}: name is not an exact substring of the book text (hover would never trigger)")
            continue
        f = c.get("first")
        ok = isinstance(f, list) and len(f) == 2 and text_of(f[0], f[1]) is not None and name in text_of(f[0], f[1])
        if not ok:
            if fix:
                c["first"] = list(first)
            else:
                errors.append(f"concept {name!r}: 'first' {f} does not contain the name; real first occurrence is {list(first)} (--fix)")
        elif tuple(f) != first:
            if fix:
                c["first"] = list(first)
            else:
                warnings.append(f"concept {name!r}: 'first' {f} is not the earliest occurrence {list(first)}")
    # coverage
    substantial = [i for i, ch in enumerate(chs) if sum(len(p) for p in ch["paras"]) >= 1500]
    no_entry = [i for i in substantial if str(i) not in (D.get("entry") or {})]
    if no_entry:
        warnings.append(f"{len(no_entry)}/{len(substantial)} substantial chapters have no chapter entry: {no_entry[:20]}")
    no_notes = [i for i in substantial if not (D.get("notes") or {}).get(str(i))]
    if no_notes:
        warnings.append(f"{len(no_notes)}/{len(substantial)} substantial chapters have no margin notes: {no_notes[:20]}")
    nconc = len(D.get("concepts") or [])
    if nconc < 5 and len(substantial) >= 3:
        warnings.append(f"only {nconc} concept cards")
    stats = {"chapters": len(chs), "substantial_chapters": len(substantial), "entries": len(D.get("entry") or {}),
             "notes": total_notes, "quiz_chapters": len(D.get("quiz") or {}), "concepts": nconc}
    return errors, warnings, stats


def merge(parts_dir):
    D = {"entry": {}, "notes": {}, "quiz": {}, "concepts": []}
    bp = os.path.join(parts_dir, "book.json")
    if os.path.exists(bp):
        with open(bp, encoding="utf-8") as f:
            b = json.load(f)
        D["subtitle"] = b.get("subtitle", "")
        D["concepts"] += b.get("concepts", [])
    for path in sorted(glob.glob(os.path.join(parts_dir, "ch-*.json"))):
        with open(path, encoding="utf-8") as f:
            part = json.load(f)
        k = str(part.get("chapter", int(re.search(r"ch-(\d+)", path).group(1))))
        if part.get("entry"):
            D["entry"][k] = part["entry"]
        if part.get("notes"):
            D["notes"][k] = part["notes"]
        if part.get("quiz"):
            D["quiz"][k] = part["quiz"]
        D["concepts"] += part.get("concepts", [])
    seen, out = set(), []
    for c in D["concepts"]:  # first definition of a name wins; later chapters may only add relations
        key = c.get("name")
        if key in seen:
            prev = next(x for x in out if x.get("name") == key)
            prev["rel"] = list(dict.fromkeys((prev.get("rel") or []) + (c.get("rel") or [])))
            continue
        seen.add(key)
        out.append(c)
    D["concepts"] = out
    return D


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("ir")
    c.add_argument("distill")
    c.add_argument("--fix", action="store_true", help="re-anchor quotes/first occurrences, estimate times, write back")
    c.add_argument("--legacy", action="store_true", help="v1 distills without quotes")
    m = sub.add_parser("merge")
    m.add_argument("ir")
    m.add_argument("parts")
    m.add_argument("out")
    a = ap.parse_args()
    with open(os.path.join(a.ir, "book.json"), encoding="utf-8") as f:
        book = json.load(f)
    if a.cmd == "merge":
        D = merge(a.parts)
        errors, warnings, stats = check(book, D, fix=True)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(D, f, ensure_ascii=False, indent=1)
    else:
        with open(a.distill, encoding="utf-8") as f:
            D = json.load(f)
        errors, warnings, stats = check(book, D, fix=a.fix, legacy=a.legacy)
        if a.fix:
            with open(a.distill, "w", encoding="utf-8") as f:
                json.dump(D, f, ensure_ascii=False, indent=1)
    print(json.dumps({"ok": not errors, "stats": stats, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=1))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
