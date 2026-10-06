#!/usr/bin/env node
// lecture-me-with-html — paged lecture builder
// 解析逐页 lecture 源稿 → KaTeX 服务端渲染数学 → 组装进翻页模板。
// 设计血统:book-distiller 阅读器 tokens;数学离线(字体内联)。
// 用法: node lecture.mjs build lecture.md -o out.html [--lint-only] [--no-open]
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const req = createRequire(import.meta.url);

/* ---------- args ---------- */
const args = process.argv.slice(2);
const cmd = args[0];
const flag = (f) => args.includes(f);
const argOf = (f) => { const i = args.indexOf(f); return i >= 0 ? args[i + 1] : undefined; };
if (cmd !== "build" || !args[1]) {
  console.log("用法: lecture.mjs build <lecture.md> [-o out.html] [--lint-only] [--no-open]");
  process.exit(cmd === "help" ? 0 : 1);
}
const SRC = resolve(args[1]);
const OUT = resolve(argOf("-o") || basename(SRC).replace(/\.md$/i, ".html"));

/* ---------- katex (optional, degrade gracefully) ---------- */
function loadKatex() {
  const tries = [() => req("katex"), () => req(join(process.cwd(), "node_modules", "katex")),
    () => req(join(SCRIPT_DIR, "node_modules", "katex"))];
  for (const t of tries) { try { return t(); } catch (_) {} }
  return null;
}
const KATEX = loadKatex();

/* ---------- source ---------- */
const raw = readFileSync(SRC, "utf8").replace(/\r\n/g, "\n");

/* frontmatter (simple key: value + one nesting level) */
let meta = { title: "Lecture", subtitle: "", date: "", learner: {} };
let body = raw;
const fm = raw.match(/^---\n([\s\S]*?)\n---\n/);
if (fm) {
  body = raw.slice(fm[0].length);
  let lastKey = null;
  for (const line of fm[1].split("\n")) {
    const m = line.match(/^(\w+):\s*(.*)$/);
    const sub = line.match(/^\s+(\w+):\s*(.*)$/);
    if (m) { if (m[1] === "learner") { meta.learner = {}; lastKey = "learner"; } else { meta[m[1]] = m[2].trim(); lastKey = null; } }
    else if (sub && lastKey === "learner") meta.learner[sub[1]] = sub[2].trim();
  }
}

/* bib block: global source registry */
const BIB = {};
const bibRe = /```bib\n([\s\S]*?)```/g; let bm;
while ((bm = bibRe.exec(body))) {
  for (const line of bm[1].split("\n")) {
    const m = line.match(/^\s*(S\d+)\s*:\s*\[([^\]]+)\]\((\S+)\)\s*(?:—|-)\s*(.*)$/);
    if (m) BIB[m[1]] = { id: m[1], title: m[2], url: m[3], meta: m[4] };
  }
}
body = body.replace(/```bib\n[\s\S]*?```\n?/g, "");

/* ---------- pages ---------- */
const pageRe = /^## (P\d+)([^\n]*)$/gm;
const marks = []; let pm;
while ((pm = pageRe.exec(body))) {
  let rest = pm[2];
  const om = rest.match(/\{([^}]*)\}\s*$/);
  const opts = {};
  if (om) {
    rest = rest.slice(0, om.index).trim();
    for (const kv of om[1].split(/\s+/)) {
      const [k, v] = kv.split("=");
      if (k) opts[k.trim()] = (v || "true").trim();
    }
  }
  const title = rest.replace(/^[\s·:.\-—]+/, "").trim();
  marks.push({ id: pm[1], title, opts, start: pm.index + pm[0].length, head: pm.index });
}
const pages = marks.map((mk, i) => ({
  id: mk.id, title: mk.title, opts: mk.opts,
  md: body.slice(mk.start, i + 1 < marks.length ? marks[i + 1].head : body.length).trim()
}));

/* ---------- lint ---------- */
const BANNED = [/显然可得/g, /显然有/g, /易得/g, /经过简单计算/g, /不难看出/g, /它是显然/g,
  /it\s+is\s+obvious/gi, /after\s+some\s+algebra/gi, /it\s+can\s+be\s+shown/gi, /trivially/gi];
let warnings = [], errors = [];
const expectNum = (i) => "P" + String(i + 1).padStart(2, "0");
pages.forEach((p, i) => {
  if (p.id !== expectNum(i)) errors.push(`页码断档:第 ${i + 1} 页是 ${p.id},应为 ${expectNum(i)}`);
  for (const b of BANNED) if (b.test(p.md)) errors.push(`${p.id} 含数学瞬移用语(/${b.source}/)`);
  if (!/```sources/.test(p.md)) warnings.push(`${p.id} 无 sources 块(该页结论无来源锚)`);
});
if (!BIB || Object.keys(BIB).length === 0) warnings.push("缺少 bib 全局来源清单");
if (!pages.some(p => /```quiz/.test(p.md))) warnings.push("全文无 quiz 测验块");
/* visual-layer lint:theater 文字量 / 核心链视觉 / 对象连续性 */
const cjk = (s) => (s.match(/[\u4e00-\u9fff]/g) || []).length;
for (const p of pages) {
  if (p.opts && (p.opts.mode === "theater" || p.opts.mode === "derive")) {
    const prose = p.md.split("```")[0] || "";
    if (cjk(prose) > 120) warnings.push(`${p.id} mode=${p.opts.mode} 首屏正文 ${cjk(prose)} 字(建议 ≤120):把严谨内容挪进 \`\`\`notes\`\`\``);
  }
}
const coreChain = pages.slice(0, Math.min(11, pages.length));
for (const p of coreChain) {
  if (!/```(scene|visual|svg|lab)/.test(p.md))
    warnings.push(`${p.id} 属于核心教学链(P01–P11)但没有 scene/visual/lab`);
}
{
  const objPage = new Map();
  for (const p of pages) {
    const objs = (p.opts && p.opts.objects ? p.opts.objects.split(",") : []);
    if (!objs.length) continue;
    const svgText = [...p.md.matchAll(/<svg[\s\S]*?<\/svg>/g)].map(m => m[0]).join("");
    for (const o of objs) {
      if (!svgText.includes(`data-obj="${o.trim()}"`))
        warnings.push(`${p.id} 声明 objects 含 ${o.trim()},但其 SVG 中没有 data-obj="${o.trim()}"`);
    }
    objPage.set(p.id, objs.map(x => x.trim()));
  }
  for (const p of pages) {
    const inh = p.opts && p.opts.inherits;
    if (!inh || !objPage.has(inh)) continue;
    const shared = (objPage.get(inh) || []).filter(o => (p.opts.objects || "").includes(o));
    if (!shared.length)
      warnings.push(`${p.id} inherits=${inh},但与它没有任何共同延续对象(视觉连续性断裂)`);
  }
}
if (pages.length === 0) errors.push("没有找到任何页面(需要 ## P01 · 标题 格式)");

/* ---------- markdown-lite + math ---------- */
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
function renderMath(tex, display) {
  if (!KATEX) return `<code class="math-fallback">${esc(tex)}</code>`;
  try {
    return KATEX.renderToString(tex, { displayMode: display, throwOnError: false, output: "html", strict: false });
  } catch (e) {
    errors.push(`KaTeX 渲染失败: ${e.message.slice(0, 120)} — "${tex.slice(0, 60)}"`);
    return `<code class="math-fallback">${esc(tex)}</code>`;
  }
}
function mathPass(md) {
  const store = []; 
  md = md.replace(/\$\$([\s\S]+?)\$\$/g, (_, t) => { store.push(renderMath(t.trim(), true)); return "\x00D" + (store.length - 1) + "\x00"; });
  md = md.replace(/\$([^$\n]+?)\$/g, (_, t) => { store.push(renderMath(t.trim(), false)); return "\x00I" + (store.length - 1) + "\x00"; });
  return { md, store };
}
function inline(s) {
  return s
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*\n]+)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}
function mdToHtml(md) {
  const { md: m0, store } = mathPass(md);
  const lines = esc(m0).split("\n");
  let out = [], i = 0;
  const flushP = (buf) => { if (buf.length) out.push("<p>" + buf.map(inline).join("<br>") + "</p>"); };
  let buf = [];
  while (i < lines.length) {
    const L = lines[i];
    if (/^\s*$/.test(L)) { flushP(buf); buf = []; i++; continue; }
    if (/^### /.test(L)) { flushP(buf); buf = []; out.push("<h2>" + inline(L.slice(4)) + "</h2>"); i++; continue; }
    if (/^-{3,}$/.test(L.trim())) { flushP(buf); buf = []; out.push("<hr>"); i++; continue; }
    if (/^&gt; /.test(L)) { flushP(buf); buf = []; const q = []; while (i < lines.length && /^&gt; /.test(lines[i])) { q.push(lines[i].slice(5)); i++; } out.push("<blockquote>" + q.map(inline).join("<br>") + "</blockquote>"); continue; }
    if (/^\|/.test(L)) {
      flushP(buf); buf = [];
      const rows = []; while (i < lines.length && /^\|/.test(lines[i])) { rows.push(lines[i]); i++; }
      const cells = (r) => r.split("|").slice(1, -1).map(c => c.trim());
      if (rows.length > 1 && /^[\s|:\-]+$/.test(rows[1])) {
        let t = "<table><thead><tr>" + cells(rows[0]).map(c => "<th>" + inline(c) + "</th>").join("") + "</tr></thead><tbody>";
        for (const r of rows.slice(2)) t += "<tr>" + cells(r).map(c => "<td>" + inline(c) + "</td>").join("") + "</tr>";
        out.push(t + "</tbody></table>");
      } else out.push("<p>" + inline(rows.join(" ")) + "</p>");
      continue;
    }
    if (/^[-*] /.test(L)) {
      flushP(buf); buf = [];
      const items = []; while (i < lines.length && /^[-*] /.test(lines[i])) { items.push(lines[i].slice(2)); i++; }
      out.push("<ul>" + items.map(x => "<li>" + inline(x) + "</li>").join("") + "</ul>"); continue;
    }
    if (/^\d+\. /.test(L)) {
      flushP(buf); buf = [];
      const items = []; while (i < lines.length && /^\d+\. /.test(lines[i])) { items.push(lines[i].replace(/^\d+\. /, "")); i++; }
      out.push("<ol>" + items.map(x => "<li>" + inline(x) + "</li>").join("") + "</ol>"); continue;
    }
    buf.push(L); i++;
  }
  flushP(buf);
  let html = out.join("\n");
  html = html.replace(/\x00([DI])(\d+)\x00/g, (_, k, n) => store[+n]);
  return html;
}
function parseQuiz(blk, pid, n) {
  const lines = blk.split("\n").map(x => x.trim()).filter(Boolean);
  const q = []; const opts = []; let fb = [];
  let mode = "q";
  for (const L of lines) {
    if (L.startsWith("??")) { mode = "fb"; fb.push(L.replace(/^\?\?\s*/, "")); continue; }
    if (/^-\s\[x\]\s/.test(L)) { opts.push({ t: L.replace(/^-\s\[x\]\s/, ""), ok: true }); mode = "opts"; continue; }
    if (/^-\s/.test(L)) { opts.push({ t: L.replace(/^-\s/, ""), ok: false }); mode = "opts"; continue; }
    (mode === "fb" ? fb : q).push(L);
  }
  let h = `<div class="quiz"><span class="qtag">SELF TEST · ${pid} · Q${n}</span><span>${esc(q.join(" "))}</span>`;
  if (opts.length) for (const o of opts) h += `<button${o.ok ? ' data-ok="1"' : ""}>${esc(o.t)}</button>`;
  else h += `<button data-reveal="1">查看参考答案</button>`;
  h += `<span class="fb">${esc(fb.join("\n"))}</span></div>`;
  return h;
}
function parseSources(blk) {
  const ids = blk.split(/[\s,]+/).map(x => x.trim()).filter(x => /^S\d+$/.test(x));
  let h = `<div class="srcs"><span class="lbl">SOURCES</span>`;
  for (const id of ids) {
    const s = BIB[id];
    h += s ? `<a href="${esc(s.url)}" target="_blank" rel="noopener" title="${esc(s.title)} — ${esc(s.meta)}">${id}</a>`
           : `<span>${id}(未在 bib 中登记)</span>`;
  }
  return h + `</div>`;
}
/* scene:SVG(含 data-beat 分组)+ <bN>旁白</bN> → 可逐拍推进的剧场 */
function parseScene(blk) {
  const caps = [...blk.matchAll(/<b(\d+)>([\s\S]*?)<\/b\1>/g)].map(m => ({ n: +m[1], t: m[2].trim() }));
  const svgs = [...blk.matchAll(/<svg[\s\S]*?<\/svg>/g)].map(m => m[0]).join("\n");
  let beats = 0;
  for (const m of svgs.matchAll(/data-beat="(\d+)"/g)) beats = Math.max(beats, +m[1]);
  for (const c of caps) beats = Math.max(beats, c.n);
  const cap = {};
  caps.forEach(c => cap[c.n] = c.t);
  let capHtml = "";
  for (let k = 1; k <= beats; k++) {
    let t = cap[k] !== undefined
      ? esc(cap[k]).replace(/\$([^$\n]+?)\$/g, (_, tex) => renderMath(tex, false))
      : "\u00a0";
    capHtml += `<span class="bcap" data-b="${k}">${t}</span>`;
  }
  return `<div class="scene" data-beats="${beats}">` +
    `<div class="capbar"><span class="bcount">BEAT 1/${beats} · 点击或按 → 继续</span>${capHtml}</div>` +
    `<div class="stage">${svgs}</div></div>`;
}
function parseNotes(blk) {
  return `<div class="notes"><div class="ntag">NOTES · 严谨层(方程/假设/来源细节,点开看)</div>` +
    `<div class="nbody">${mdToHtml(blk)}</div></div>`;
}

/* ---------- page assembly ---------- */
const pagesHtml = pages.map((p, i) => {
  let md = p.md;
  /* fenced extensions */
  const fence = /```(sources|quiz|capsule|lab|bib|callout|visual|svg|scene|notes|predict)([^\n]*)\n([\s\S]*?)```/g;
  const slots = [];
  md = md.replace(fence, (_, kind, info, blk) => {
    const ph = "\x00F" + slots.length + "\x00"; slots.push({ kind, info: info.trim(), blk }); return ph;
  });
  let html = mdToHtml(md);
  let qn = 0;
  for (const s of slots) {
    let rep = "";
    if (s.kind === "sources") rep = parseSources(s.blk);
    else if (s.kind === "quiz") rep = parseQuiz(s.blk, p.id, ++qn);
    else if (s.kind === "lab") rep = `<div class="lab">${s.blk}</div>`;
    else if (s.kind === "capsule") rep = `<div class="capsule"><span class="ctag">PREREQUISITE CAPSULE · ${esc(s.info || "K")}</span>${mdToHtml(s.blk)}</div>`;
    else if (s.kind === "callout") rep = `<div class="callout"><b>${esc(s.info)}</b>${mdToHtml(s.blk)}</div>`;
    else if (s.kind === "visual" || s.kind === "svg") rep = `<div class="visual">${s.blk}</div>`;
    else if (s.kind === "scene") rep = parseScene(s.blk);
    else if (s.kind === "notes") rep = parseNotes(s.blk);
    else if (s.kind === "predict") { const q = parseQuiz(s.blk, p.id, ++qn); rep = q.replace('class="quiz"', 'class="quiz predict"').replace(/SELF TEST/, "PREDICT · 先猜再看"); }
    else if (s.kind === "bib") rep = "";
    html = html.replace("\x00F" + slots.indexOf(s) + "\x00", rep);
  }
  const num = String(i + 1).padStart(2, "0");
  const o = p.opts || {};
  return `<section class="page" data-id="${p.id}" data-foot="${esc(p.title)}"` +
    (o.mode ? ` data-mode="${esc(o.mode)}"` : "") +
    (o.objects ? ` data-objects="${esc(o.objects)}"` : "") +
    (o.inherits ? ` data-inherits="${esc(o.inherits)}"` : "") + `>` +
    `<div class="sheet"><div class="kicker">PAGE ${num} / ${String(pages.length).padStart(2, "0")} · ${p.id}` +
    (o.mode ? ` · ${esc(o.mode).toUpperCase()}` : "") + `</div>` +
    `<h1 class="pt">${esc(p.title)}</h1>${html}</div></section>`;
}).join("\n");

const tocHtml = pages.map((p, i) =>
  `<button class="tocitem" data-i="${i}"><span class="n">${p.id}</span>${esc(p.title)}</button>`).join("\n");
const tierOf = (m) => (m.meta.match(/tier\s*A|权威|原始|教材|review|论文|官方/i) ? "Tier A · 原始与权威"
  : /tier\s*B|OCW|lecture notes|大学/i.test(m.meta) ? "Tier B · 大学教学资料"
  : /tier\s*C|直觉|3Blue|教学网站/i.test(m.meta) ? "Tier C · 优质直觉资源"
  : /tier\s*D|COMSOL|ANSYS|QuantumATK|MathWorks|Intel|TSMC|Synopsys|产业|软件/i.test(m.meta) ? "Tier D · 工程与产业"
  : /tier\s*E|SE\b|Reddit|社区|stack/i.test(m.meta) ? "Tier E · 社区讨论" : "其他来源");
const tierOrder = ["Tier A · 原始与权威", "Tier B · 大学教学资料", "Tier C · 优质直觉资源", "Tier D · 工程与产业", "Tier E · 社区讨论", "其他来源"];
const srcHtml = tierOrder.map(t => {
  const items = Object.values(BIB).filter(s => tierOf(s) === t);
  if (!items.length) return "";
  return `<div class="srcgroup">${t}</div>` + items.map(s =>
    `<div class="srcitem"><span class="sid">${s.id}</span><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a> — ${esc(s.meta)}</div>`).join("");
}).join("\n");

/* ---------- math css inline (fonts as data uri) ---------- */
function mathCss() {
  if (!KATEX) return "";
  try {
    const dist = dirname(req.resolve("katex/dist/katex.min.css"));
    let css = readFileSync(join(dist, "katex.min.css"), "utf8");
    const FONTS = ["Main-Regular","Main-Italic","Main-Bold","Main-BoldItalic","Math-Italic","Math-BoldItalic",
      "AMS-Regular","Size1-Regular","Size2-Regular","Size3-Regular","Size4-Regular",
      "SansSerif-Regular","SansSerif-Italic","SansSerif-Bold","Script-Regular","Caligraphic-Regular","Typewriter-Regular"];
    css = css.replace(/url\(fonts\/KaTeX_([\w-]+)\.woff2\)/g, (_, f) => {
      const p = join(dist, "fonts", `KaTeX_${f}.woff2`);
      if (!FONTS.includes(f) || !existsSync(p)) return "url(data:,)";
      return `url(data:font/woff2;base64,${readFileSync(p).toString("base64")})`;
    });
    return css;
  } catch (e) { warnings.push("KaTeX CSS 内联失败: " + e.message.slice(0, 80)); return ""; }
}

/* ---------- assemble ---------- */
const template = readFileSync(join(SCRIPT_DIR, "..", "assets", "lecture-template.html"), "utf8");
const learner = meta.learner || {};
const LBL = { math_level: "数学", physics_level: "物理", domain_level: "领域" };
const learnerTxt = Object.entries(learner).map(([k, v]) => (LBL[k] || k) + ": " + v).join(" · ");
const html = template
  .replaceAll("{{TITLE}}", esc(meta.title || "Lecture"))
  .replace("{{SUBTITLE}}", esc((meta.subtitle || "") + (learnerTxt ? " · " + learnerTxt : "")))
  .replace("{{TOTAL}}", String(pages.length).padStart(2, "0"))
  .replace("{{FOOTTITLE}}", esc(pages[0] ? pages[0].title : ""))
  .replace("{{PAGES}}", pagesHtml)
  .replace("{{TOC}}", tocHtml)
  .replace("{{ALLSOURCES}}", srcHtml)
  .replace("{{MATH_CSS}}", mathCss())
  .replace("{{KEYJSON}}", JSON.stringify({ page: "lecture:" + (meta.title || "x") + ":page", mode: "lecture:" + (meta.title || "x") + ":mode", beat: "lecture:" + (meta.title || "x") + ":beats" }));

/* ---------- dossier audit (--dossier) ---------- */
const DOSSIER = argOf("--dossier");
const claims = new Map(); // id -> {sources:[], conf, used:[]}
const dossierSources = new Set();
if (DOSSIER) {
  if (!existsSync(DOSSIER)) { errors.push(`dossier 文件不存在: ${DOSSIER}`); }
  else {
    const d = readFileSync(DOSSIER, "utf8");
    for (const line of d.split("\n")) {
      const cm = line.match(/^\|\s*(C\d+)\s*\|/);
      if (cm) {
        // 表格单元里的 \| 是 LaTeX 转义管道,先保护再切列
        const cells = line.replace(/\\\|/g, "\u0001").split("|").map(x => x.replace(/\u0001/g, "\\|").trim());
        // | ID | Claim | Type | 来源 | 置信 | 假设 | 用于 |
        claims.set(cm[1], {
          sources: (cells[4] || "").match(/S\d+/g) || [],
          conf: (cells[5] || "high").toLowerCase(),
          used: (cells[7] || "").match(/P\d+/g) || []
        });
      }
      const sm = line.match(/^\s*-\s*\*\*(S\d+)\*\*/);
      if (sm) dossierSources.add(sm[1]);
    }
    /* claim integrity: lecture 引用的 Cxxx 必须在 dossier 中存在 */
    for (const p of pages) {
      for (const m of p.md.matchAll(/\bC\d{3}\b/g)) {
        if (!claims.has(m[0])) errors.push(`${p.id} 引用 ${m[0]},但 dossier 的 Claim Ledger 中没有它`);
      }
    }
    /* source integrity: claim 的来源必须在 dossier Sources 中登记 */
    for (const [id, c] of claims) {
      for (const s of c.sources) {
        if (!dossierSources.has(s)) errors.push(`${id} 的来源 ${s} 未在 dossier Sources 区登记`);
      }
    }
    /* claim-to-page: used-in 声明与实际引用互相核对 */
    const citedOn = new Map();
    for (const p of pages) for (const m of p.md.matchAll(/\bC\d{3}\b/g)) {
      const id = m[0]; if (!claims.has(id)) continue;
      if (!citedOn.has(id)) citedOn.set(id, new Set());
      citedOn.get(id).add(p.id);
    }
    for (const [id, c] of claims) {
      const used = c.used, actual = [...(citedOn.get(id) || [])];
      for (const pg of used) if (!actual.some(a => a === pg)) warnings.push(`${id} 声明用于 ${pg},但该页未引用它`);
      for (const pg of actual) if (!used.includes(pg)) warnings.push(`${id} 在 ${pg} 被引用,但 used-in 未声明(补账)`);
      if (actual.length === 0) warnings.push(`${id} 是孤儿 claim:没有任何页面引用`);
    }
    /* confidence: medium/low claim 所在页必须出现缓和语 */
    const HEDGE = [/约/, /近似/, /据报道/, /一种说法/, /预印本/, /大致/, /可能/, /区间/, /据.*记载/, /medium/i];
    for (const [id, c] of claims) {
      if (c.conf !== "medium" && c.conf !== "low") continue;
      for (const p of pages) {
        if (!p.md.includes("[" + id + "]")) continue;
        if (!HEDGE.some(h => h.test(p.md)))
          warnings.push(`${id} 置信为 ${c.conf},但 ${p.id} 页面缺少缓和措辞(约/近似/预印本…)`);
      }
    }
    /* orphan bib sources: 没有任何页面 sources 块引用 */
    const pageSrcIds = new Set();
    for (const p of pages) for (const m of p.md.matchAll(/```sources\n([\s\S]*?)```/g))
      for (const s of m[1].match(/S\d+/g) || []) pageSrcIds.add(s);
    for (const s of Object.keys(BIB)) if (!pageSrcIds.has(s)) warnings.push(`来源 ${s} 是孤儿:没有任何页面引用`);
  }
}

/* ---------- report ---------- */
function statLine() {
  const n = (re) => pages.reduce((a, p) => a + (p.md.match(re) || []).length, 0);
  const scenes = n(/```scene/g);
  const totalBeats = pages.reduce((a, p) => {
    let b = 0;
    for (const sm of p.md.matchAll(/```scene[^\n]*\n([\s\S]*?)```/g)) {
      let mx = 0; for (const m of sm[1].matchAll(/data-beat="(\d+)"/g)) mx = Math.max(mx, +m[1]);
      for (const m of sm[1].matchAll(/<b(\d+)>/g)) mx = Math.max(mx, +m[1]);
      b += mx;
    }
    return a + b;
  }, 0);
  return `pages=${pages.length} bibSources=${Object.keys(BIB).length} claims=${DOSSIER ? claims.size : "n/a"} ` +
    `quiz=${n(/```quiz/g)} predict=${n(/```predict/g)} scenes=${scenes} beats≈${totalBeats} ` +
    `visual=${n(/```(?:visual|svg)/g)} labs=${n(/```lab/g)} notes=${n(/```notes/g)}`;
}
for (const w of warnings) console.log(`⚠ ${w}`);
if (errors.length) {
  for (const e of errors) console.error(`✗ ${e}`);
  console.error(`✗ lint 未通过(${errors.length} 个错误,${warnings.length} 个警告),不写文件。`);
  process.exit(1);
}
if (flag("--lint-only")) {
  console.log(`✓ lint 通过:${statLine()} warnings=${warnings.length}`);
  process.exit(0);
}
mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, html);
const kb = Math.round(html.length / 1024);
console.log(`✓ ${OUT}`);
console.log(`  ${statLine()} · ${kb} KB · 数学:${KATEX ? "KaTeX 服务端渲染(离线)" : "降级为等宽块(未安装 katex)"}`);
if (!flag("--no-open")) {
  try { const start = process.platform === "win32" ? "cmd" : "open";
    const a = process.platform === "win32" ? ["/c", "start", "", OUT] : [OUT];
    execSync(`${start} ${a.map(x => `"${x}"`).join(" ")}`, { stdio: "ignore", shell: false });
  } catch (_) {}
}
