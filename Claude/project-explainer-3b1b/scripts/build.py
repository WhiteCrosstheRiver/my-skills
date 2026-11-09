#!/usr/bin/env python3
"""Build a single self-contained explainer HTML from report.json.

usage: python build.py report.json out.html [--template path/to/template.html]

- Figure blocks may use "file": "relative/path.svg|png" (relative to the
  report); the file is inlined as a data: URI so the page is one portable file.
- {"$include": "data/x.json"} anywhere in the report is replaced by that file's
  JSON, so large extracted arrays live in data/ and can be regenerated alone.
- The report JSON is embedded verbatim (no re-serialisation), so key order,
  Unicode and formatting are preserved.
- template.html next to this script (vendored copy) wins over ../assets/.
"""
import base64, json, mimetypes, pathlib, re, sys

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    report_p, out_p = pathlib.Path(args[0]), pathlib.Path(args[1])
    here = pathlib.Path(__file__).resolve().parent
    tpl_p = here / "template.html"                      # vendored copy wins
    if not tpl_p.exists():
        tpl_p = here.parent / "assets" / "template.html"
    if "--template" in args:
        tpl_p = pathlib.Path(args[args.index("--template") + 1])

    raw = report_p.read_text(encoding="utf-8")
    # {"$include": "data/x.json"} -> that file's JSON (keeps big arrays out of report.json)
    raw = re.sub(r'\{\s*"\$include"\s*:\s*"([^"]+)"\s*\}',
                 lambda m: (report_p.parent / m.group(1)).read_text(encoding="utf-8").strip(), raw)
    data = json.loads(raw)  # validate early: fails loudly on bad JSON

    def inline(m):
        f = (report_p.parent / m.group(1)).resolve()
        mime = mimetypes.guess_type(f.name)[0] or ("image/svg+xml" if f.suffix == ".svg" else "application/octet-stream")
        b64 = base64.b64encode(f.read_bytes()).decode("ascii")
        return f'"src": "data:{mime};base64,{b64}"'
    raw = re.sub(r'"file"\s*:\s*"([^"]+)"', inline, raw)

    title = data.get("meta", {}).get("short") or "Explainer"
    if isinstance(title, dict):
        title = title.get("en") or next(iter(title.values()))
    html = tpl_p.read_text(encoding="utf-8")
    html = html.replace("/*__REPORT_JSON__*/", raw.replace("</", "<\\/"))
    html = html.replace("__TITLE__", title)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(html, encoding="utf-8")
    print(f"wrote {out_p} ({out_p.stat().st_size/1024:.0f} KB)")

if __name__ == "__main__":
    main()
