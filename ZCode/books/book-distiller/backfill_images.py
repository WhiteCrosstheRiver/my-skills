# -*- coding: utf-8 -*-
"""全量回填:对 manifest 里 ir_ready 的书做 v2 图片抽取 + 重建已完成书的 HTML。
阶段1:已完成(out 存在)的书优先;阶段2:未完成的书只升级 IR(供后续 agent 构建时自带图)。
用法: python backfill_images.py
"""
import json, os, sys, subprocess, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "蒸馏书库")
LOG = os.path.join(HERE, "batch", "backfill.log")

def log(msg):
    line = str(msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf8") as f:
        f.write(line + "\n")

def main():
    sys.path.insert(0, HERE)
    from extract_images_v2 import build_v2
    m = json.load(open(os.path.join(HERE, "batch", "manifest.json"), encoding="utf8"))
    recs = [r for r in m if r.get("status") == "ir_ready"]
    done = [r for r in recs if os.path.exists(r["out"])]
    todo = [r for r in recs if not os.path.exists(r["out"])]
    log(f"backfill start: done_books={len(done)} pending_books={len(todo)}")
    ok_n = fail_n = skip_n = 0
    # 阶段1:已完成的书
    for i, r in enumerate(done):
        try:
            bp = os.path.join(r["ir"], "book.json")
            book = json.load(open(bp, encoding="utf8"))
            if book.get("images_total") is None:
                ok, total, msg = build_v2(r["ir"], apply=True)
                if not ok:
                    log(f"[{i+1}/{len(done)}] V2FAIL {r['slug'][:36]} | {msg}"); fail_n += 1; continue
            else:
                total = book["images_total"]
            d = os.path.join(HERE, "batch", "distill", os.path.basename(r["ir"]) + ".json")
            p = subprocess.run([sys.executable, os.path.join(HERE, "build_book.py"), r["ir"],
                                d if os.path.exists(d) else os.path.join(HERE, "batch", "_empty.json"),
                                r["out"], r["slug"]], capture_output=True, text=True)
            if "written" in p.stdout:
                ok_n += 1
                if i % 10 == 0: log(f"[{i+1}/{len(done)}] ok {r['slug'][:36]} imgs={total/1024/1024:.1f}MB")
            else:
                fail_n += 1
                log(f"[{i+1}/{len(done)}] BUILDFAIL {r['slug'][:36]} | {p.stdout[-120:]} {p.stderr[-200:]}")
        except Exception as e:
            fail_n += 1
            log(f"[{i+1}/{len(done)}] EXC {r['slug'][:36]} | {e}")
    log(f"phase1 done: rebuilt={ok_n} fail={fail_n}")
    # 阶段2:未完成的书,只升级 IR(图片就位,后续构建自带)
    up = 0
    for i, r in enumerate(todo):
        try:
            bp = os.path.join(r["ir"], "book.json")
            book = json.load(open(bp, encoding="utf8"))
            if book.get("images_total") is None:
                ok, total, msg = build_v2(r["ir"], apply=True)
                up += 1 if ok else 0
                if not ok: log(f"[p2 {i+1}/{len(todo)}] V2FAIL {r['slug'][:36]} | {msg}")
            else:
                skip_n += 1
        except Exception as e:
            log(f"[p2 {i+1}/{len(todo)}] EXC {r['slug'][:36]} | {e}")
    log(f"backfill COMPLETE: rebuilt={ok_n} fail={fail_n} pending_ir_upgraded={up}")

if __name__ == "__main__":
    main()
