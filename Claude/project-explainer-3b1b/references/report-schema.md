# report.json schema

`T` below means a translatable string: either `"plain text"` or `{"en": "...", "zh": "..."}`.
Strings may contain inline HTML (`<b>`, `<em>`, `<span class="c-yellow">`, `<br>`) and inline math `$...$` (KaTeX).
Colour classes: `c-blue c-teal c-green c-yellow c-gold c-red c-purple c-muted`. Tones: `blue teal green yellow gold red maroon purple grey`.
States: `done doing todo fail skip`.

```jsonc
{
  "meta": {
    "short": "CNT-MLP",                       // brand in top bar + <title>
    "title": T, "subtitle": T, "kicker": T,
    "languages": ["en", "zh"], "defaultLang": "en",
    "updated": T, "note": T
  },
  "ui": { "zh": { "langName": "中文" }, "ja": { "langName": "日本語", "done": "完了", ... } },  // optional overrides
  "hero": { "chips": [{ "value": T, "label": T, "tone": "green" }], "blocks": [ /* blocks */ ] },
  "sections": [
    { "id": "motivation", "kicker": T, "navLabel": T, "title": T, "lead": T, "blocks": [ /* blocks */ ] }
  ],
  "sources": [T]
}
```

UI keys (defaults exist for `en` and `zh`): `langName theme updated sources source done doing todo fail skip fieldOn fieldOff paired field solvent rstar lowered zeroField distance energy`.

Anywhere a value is expected, `{"$include": "data/x.json"}` is replaced at build time by that file's JSON (path relative to report.json). Use it for extracted arrays so they can be regenerated without touching the content.

## Blocks

Every block accepts optional `source` (string path or T), `id`, `class`.

| type | fields |
|---|---|
| `p` | `text` |
| `math` | `tex` (display LaTeX), `caption` |
| `callout` | `tone`, `title`, `text` |
| `stats` | `items: [{value, unit, label, note, tone}]` |
| `list` | `items: [T or {text, state}]`, `pills: true` shows state pills |
| `cards` | `items: [{kicker, title, text, tone, state}]` |
| `columns` | `cols: [[blocks], [blocks]]` (stacks on phones) |
| `table` | `head: [T]`, `rows: [[T or {state, text}]]` |
| `pipeline` | `steps: [{label, sub, tone, state}]` |
| `roadmap` | `items: [{id, label, sub, state}]` |
| `timeline` | `items: [{date, title, text, state, tone}]` |
| `figure` | `file` (path relative to report.json, inlined at build) or `src`; `title`, `caption`, `invert` |
| `scene` | `name` (`nanotube`, `coulombTilt`, or one you add), `params`, `caption` |
| `bar` | `title, categories:[T], series:[{name, tone, values:[n], labels?:[T]}], threshold:{value,label}, scale:"linear|log", min, max, yLabel, caption` |
| `strip` | `title, groups:[{key,label}], points:[{g, v, s}], colorBy:{s:{tone,label}}, threshold, xLabel, max` |
| `numberline` | `title, items:[{label, min, max, scale, value (n or [lo,hi]), valueLabel, marks:[{value,label,tone}], good:[a,b], ticks}]` |
| `ranges` | `title, max, xLabel, items:[{label, lo, hi, tone, end:"crash|continue", note}], legend:[{tone,label}]` |
| `progress` | `title, points:[{x, y, state:"done|plan", note, prefix}], target:{value,label}, yLabel, max` |

### Scene params

- `nanotube`: `pairs` (6), `solvent` (26), `field` (force scale, 2.4), `coulomb` (900), `alt`.
- `coulombTilt`: `solvents: [{label, lB}]` (Bjerrum length in nm), `Emax` (V/Å), `E0`, `kT` (eV), `xmax`, `ymin`, `ymax`.
  Plots u(x) = −1/x − βx with x = r/l_B and β = eE·l_B/k_BT; marks the barrier at x* = 1/√β.

### Minimal example

```json
{
  "meta": {"short": "Demo", "title": {"en": "Demo", "zh": "示例"}, "languages": ["en", "zh"]},
  "sections": [{
    "id": "data", "title": {"en": "Key data", "zh": "关键数据"},
    "blocks": [{
      "type": "bar", "title": "Force error", "categories": ["A", "B"],
      "series": [{"name": "run 1", "tone": "blue", "values": [100.7, 76.6]}],
      "threshold": {"value": 10, "label": "gate 10 meV/Å"}, "yLabel": "meV/Å",
      "source": "records/c1.md"
    }]
  }]
}
```
