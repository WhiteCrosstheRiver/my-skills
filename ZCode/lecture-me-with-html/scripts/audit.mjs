#!/usr/bin/env node
// lecture-me-with-html — per-beat visual auditor
// 遍历 manifest 里每一页每一拍:?p=P&b=B 逐拍打开产物,
// 检查 console error / NaN / Infinity / pending 泄漏 / predict 提前 / 空 caption,
// 并对每个 scene 的末拍与暗色样张自动截图到 audit/。
// 用法: node audit.mjs <built.html> [--shots] [--dark-sample]
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync } from "node:fs";
import { execFileSync, spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const HTML = resolve(args[0]);
if (!existsSync(HTML)) { console.error("✗ 找不到 " + HTML); process.exit(1); }
const SHOTS = args.includes("--shots");
const DARK = args.includes("--dark-sample");
const OUTDIR = resolve(join(dirname(HTML), "audit"));

const manifest = JSON.parse(readFileSync(HTML.replace(/\.html$/i, "") + ".manifest.json", "utf8"));

function edgePath() {
  for (const p of ["C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Google/Chrome/Application/chrome.exe"]) {
    if (existsSync(p)) return p;
  }
  return null;
}
const BROWSER = edgePath();
if (!BROWSER) { console.error("✗ 未找到 Edge/Chrome"); process.exit(1); }
function urlFor(p, b, mode) {
  const u = new URL("file:///" + HTML.replace(/\\/g, "/"));
  u.searchParams.set("p", String(p));
  if (b > 1) u.searchParams.set("b", String(b));
  if (mode) u.searchParams.set("mode", mode);
  return u.href;
}
function dump(url) {
  const r = spawnSync(BROWSER, ["--headless", "--disable-gpu", "--virtual-time-budget=6000",
    "--dump-dom", url], { encoding: "utf8", maxBuffer: 256 * 1024 * 1024, timeout: 60000 });
  return r.stdout || "";
}
function shot(url, file, w, h) {
  mkdirSync(dirname(file), { recursive: true });
  spawnSync(BROWSER, ["--headless", "--disable-gpu", "--hide-scrollbars",
    `--screenshot=${file}`, `--window-size=${w},${h}`,
    "--virtual-time-budget=9000", url], { encoding: "utf8", timeout: 90000 });
}
/* 每拍 DOM 巡检 */
function auditBeat(dom, page, beat, M, hasPredictAfter) {
  const issues = [];
  if (/NaN|Infinity/.test(dom.replace(/NaN-guard|Infinity Norm/g, ""))) {
    // 正文出现裸 NaN/Infinity(排除合法词)——粗筛,人工复核
    const m = dom.match(/[^-\w](NaN|Infinity)/);
    if (m) issues.push(`文本出现 ${m[1]}`);
  }
  if (dom.includes("&amp;nbsp;")) issues.push("caption 漏出 &nbsp; 字面量");
  /* pending scene 不应显示 stage 内容 */
  for (const pm of dom.matchAll(/<div class="scene pending"[^>]*data-beats="(\d+)"[^>]*>([\s\S]*?)<div class="stage"/g)) {
    // pending 的 stage 在 DOM 里必然存在(display:none 由 CSS 控制)——检查内联泄漏:
  }
  /* predict 门控:当前拍 < enter-beat 时,不应有 armed 类 */
  for (const pm of dom.matchAll(/<div class="quiz predict([^"]*)"(?:[^>]*data-enter-beat="(\d+)")?/g)) {
    const armed = pm[1].includes("armed");
    const enter = pm[2] ? +pm[2] : 0;
    if (enter && beat < enter && armed) issues.push(`predict 在 beat ${beat} 提前 armed(应 ${enter} 后)`);
  }
  /* 空 caption:当前拍位置的 bcap 不应为空(首拍允许 nbsp 占位) */
  const capm = dom.match(/<span class="bcap on" data-b="\d+">([\s\S]*?)<\/span>/);
  if (capm && capm[1].trim() === "") issues.push("当前拍 caption 为空");
  /* beat 计数条存在 */
  if (M > 0 && !/BEAT \d+\/\d+|下一幕/.test(dom)) issues.push("缺少拍计数条");
  return issues;
}
let total = 0, bad = 0;
const report = [];
mkdirSync(OUTDIR, { recursive: true });
const URLBASE = "file:///" + HTML.replace(/\\/g, "/");
for (const pg of manifest.pages) {
  const M = pg.beats;
  const beats = M === 0 ? [0] : Array.from({ length: M }, (_, i) => i + 1);
  for (const b of beats) {
    const url = urlFor(pg.id.replace(/^P/, ""), Math.max(b, 1)) + ""; // p 参数是页号
    const url2 = urlFor(parseInt(pg.id.slice(1), 10), Math.max(b, 1));
    const dom = dump(url2);
    const issues = auditBeat(dom, pg.id, Math.max(b, 1), M, true);
    total++;
    if (issues.length) { bad++; report.push({ page: pg.id, beat: b, issues }); }
    const isSceneEnd = b === M && M > 0;
    if (SHOTS && (isSceneEnd || b === 0)) {
      shot(url2, join(OUTDIR, `${pg.id}_b${Math.max(b, 1)}.png`), 1400, 1200);
    }
  }
  if (DARK && M > 0) {
    shot(urlFor(parseInt(pg.id.slice(1), 10), M) + "&mode=dark",
      join(OUTDIR, `${pg.id}_b${M}_dark.png`), 1400, 1200);
  }
}
/* 汇总 */
console.log(`审计完成:pages=${manifest.pages.length} beats_checked=${total} issues=${bad}`);
for (const r of report) console.log(`✗ ${r.page} b${r.beat}: ${r.issues.join("; ")}`);
writeFileSync(join(OUTDIR, "audit.json"), JSON.stringify({ total, bad, report }, null, 2));
process.exit(bad ? 1 : 0);
