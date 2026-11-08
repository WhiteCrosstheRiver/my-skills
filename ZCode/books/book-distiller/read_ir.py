# -*- coding: utf-8 -*-
"""Read a Book IR the way a distiller must: whole chapters, with paragraph indices.

sample.py (v1) printed two 100-character openings per chapter; notes and concept cards were then
written about paragraphs nobody had read. This reader pages through the full text instead.

  python read_ir.py outline <ir_dir>                       # chapters, sizes, quality warnings, plan
  python read_ir.py chapter <ir_dir> <ch> [--from N] [--max-chars 12000]
  python read_ir.py find <ir_dir> <text> [--limit 20]      # exact-substring locator (for concepts/quotes)

Output lines look like `[3.17] paragraph text` = chapter 3 (0-based), paragraph 17 (0-based): the same
indices distill.json uses. A chapter longer than --max-chars ends with the exact command for the next page.
"""
import argparse
import json
import os
import sys


def load(ir_dir):
    with open(os.path.join(ir_dir, "book.json"), encoding="utf-8") as f:
        return json.load(f)


def outline(book):
    q = book.get("quality") or {}
    print(f"TITLE: {book['title']}  AUTHOR: {book.get('author', '')}  FORMAT: {book.get('format', '?')}  EXTRACTOR: {book.get('extractor', 'v1')}")
    print(f"chapters={len(book['chapters'])} paras={book['total_paras']} chars={sum(len(p) for c in book['chapters'] for p in c['paras'])}")
    for w in q.get("warnings", []):
        print("WARNING:", w)
    print()
    for i, ch in enumerate(book["chapters"]):
        chars = sum(len(p) for p in ch["paras"])
        heads = len(ch.get("heads", []))
        print(f"ch{i:>3}  {len(ch['paras']):>5} paras {chars:>8} chars  {heads:>3} heads  {len(ch.get('images') or []):>3} imgs  {ch['title'][:60]}")
    print("\nPLAN: read every chapter with `chapter` before writing its distill part; one part file per chapter.")


def chapter(book, ci, start, max_chars, ir_dir):
    ch = book["chapters"][ci]
    heads, frags = set(ch.get("heads", [])), set(ch.get("frags", []))
    print(f"== ch{ci} / {len(book['chapters']) - 1}  {ch['title']}  ({len(ch['paras'])} paras)")
    used, i = 0, start
    while i < len(ch["paras"]):
        p = ch["paras"][i]
        if used and used + len(p) > max_chars:
            break
        mark = "## " if i in heads else ("(formula/figure fragments) " if i in frags else "")
        print(f"[{ci}.{i}] {mark}{p}")
        used += len(p)
        i += 1
    if i < len(ch["paras"]):
        print(f"\n-- more: python read_ir.py chapter \"{ir_dir}\" {ci} --from {i}  ({len(ch['paras']) - i} paras left)")
    else:
        print(f"\n-- end of ch{ci}" + (f"; next: python read_ir.py chapter \"{ir_dir}\" {ci + 1}" if ci + 1 < len(book["chapters"]) else "; end of book"))


def find(book, needle, limit):
    n = 0
    for ci, ch in enumerate(book["chapters"]):
        for pi, p in enumerate(ch["paras"]):
            k = p.find(needle)
            if k >= 0:
                print(f"[{ci}.{pi}] …{p[max(0, k - 40):k + len(needle) + 40]}…")
                n += 1
                if n >= limit:
                    return
    if not n:
        print("NOT FOUND (concept names and quotes must be exact substrings of the text)")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("outline")
    o.add_argument("ir")
    c = sub.add_parser("chapter")
    c.add_argument("ir")
    c.add_argument("ch", type=int)
    c.add_argument("--from", dest="start", type=int, default=0)
    c.add_argument("--max-chars", type=int, default=12000)
    f = sub.add_parser("find")
    f.add_argument("ir")
    f.add_argument("text")
    f.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()
    book = load(a.ir)
    if a.cmd == "outline":
        outline(book)
    elif a.cmd == "chapter":
        if not 0 <= a.ch < len(book["chapters"]):
            sys.exit(f"chapter index out of range 0..{len(book['chapters']) - 1}")
        chapter(book, a.ch, a.start, a.max_chars, a.ir)
    else:
        find(book, a.text, a.limit)


if __name__ == "__main__":
    main()
