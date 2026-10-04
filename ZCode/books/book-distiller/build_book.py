# -*- coding: utf-8 -*-
"""通用蒸馏书 HTML 构建器(风格同悉达多)
用法: python build_book.py <ir_dir> <distill.json> <out.html> [title] [subtitle]
distill.json schema:
{
 "subtitle": str?, "author": str?, "en": bool?,           # en: 章标题是否英文书
 "entry":  {"<chapterIndex0based>": {"q":str,"route":[...],"keys":[...],"motif":str,"time":min}},
 "notes":  {"<chapterIndex0based>": [[at_para_idx,"TAG","text",("deeper")], ...]},
 "quiz":   {"<chapterIndex0based>": {"q":str,"a":[..]|str,"correct":int?,"fb":str}},
 "concepts":[{"id","name","en","one","first":[chIdx,paraIdx],"rel":[...]}]
}
"""
import json, sys, os, io, re

ir_dir, distill_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
book = json.load(open(os.path.join(ir_dir, "book.json"), encoding="utf8"))
D = json.load(open(distill_path, encoding="utf8")) if os.path.exists(distill_path) else {}

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ — Distilled Book</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
html,body{margin:0;height:100%;background:oklch(0.78 0.01 80);color:oklch(0.15 0.01 60);font-family:'Noto Sans SC','PingFang SC',sans-serif}
a{color:oklch(0.38 0.15 250);text-decoration:none}
::selection{background:oklch(0.88 0.06 250)}
#frame{position:relative;overflow:hidden;width:100vw;height:100vh;display:grid;grid-template-rows:52px minmax(0,1fr) 46px;background:oklch(0.915 0.007 80);color:oklch(0.15 0.01 60)}
header{display:flex;align-items:center;gap:14px;padding:0 14px 0 16px;border-bottom:1px solid oklch(0.82 0.01 80);background:oklch(0.988 0.003 80);min-width:0}
.htitle{display:flex;flex-direction:column;min-width:0;flex:1;line-height:1.25}
.htitle .t1{font-family:'Noto Serif SC',serif;font-weight:700;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.htitle .t2{font-size:12px;color:oklch(0.28 0.01 60);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mono{font-family:'IBM Plex Mono',monospace}
.seg{display:flex;gap:2px;padding:3px;background:oklch(0.86 0.008 80);border-radius:8px}
.seg button{border:0;background:transparent;border-radius:6px;padding:5px 12px;font-size:12.5px;color:oklch(0.36 0.01 60);cursor:pointer}
.seg button.on{background:oklch(0.99 0.004 85);color:oklch(0.15 0.01 60);box-shadow:0 1px 3px oklch(0.3 0.01 60/.15);font-weight:600}
.hbtn{display:flex;align-items:center;gap:8px;height:34px;padding:0 12px;border:1px solid oklch(0.78 0.01 80);background:oklch(0.99 0.004 85);border-radius:8px;font-size:13px;color:oklch(0.32 0.01 60);cursor:pointer}
.hbtn.bm-on{border-color:oklch(0.62 0.13 60);color:oklch(0.52 0.14 60)}
kbd{font-family:'IBM Plex Mono',monospace;font-size:10.5px;padding:1px 5px;border-radius:4px;background:oklch(0.94 0.006 80)}
.bodygrid{display:grid;grid-template-columns:264px minmax(0,1fr);min-height:0;position:relative}
nav{overflow:auto;border-right:1px solid oklch(0.82 0.01 80);background:oklch(0.94 0.006 80);display:flex;flex-direction:column;padding:10px 6px 14px}
.navlabel{font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.08em;color:oklch(0.42 0.01 60);padding:8px 10px 6px}
.toc-ch{display:flex;align-items:baseline;gap:10px;width:100%;text-align:left;border:0;background:transparent;padding:7px 10px;font-size:13.5px;color:oklch(0.28 0.01 60);cursor:pointer;border-radius:6px}
.toc-ch:hover{background:oklch(0.9 0.008 80)}
.toc-ch.active{background:oklch(0.988 0.003 80);color:oklch(0.15 0.01 60);font-weight:600;box-shadow:0 1px 4px oklch(0.3 0.01 60/.12)}
.toc-ch .n{font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:oklch(0.42 0.01 60);width:26px;flex:none;text-align:right}
.diamond{width:6px;height:6px;background:oklch(0.62 0.13 60);transform:rotate(45deg);margin-left:auto;flex:none}
.toc-sub{border:0;background:transparent;text-align:left;font-size:12.5px;color:oklch(0.36 0.01 60);padding:4px 10px 4px 52px;cursor:pointer;border-radius:5px}
.toc-sub:hover{background:oklch(0.88 0.008 80);color:oklch(0.15 0.01 60)}
.toc-sub.cur{color:oklch(0.38 0.14 250);font-weight:600}
.toc-foot{margin-top:auto;padding:16px 10px 0;display:grid;gap:8px}
.toc-foot .row{display:flex;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:11px;color:oklch(0.28 0.01 60)}
.bar{height:3px;background:oklch(0.9 0.007 80);border-radius:2px;overflow:hidden}
.bar>div{height:100%;width:0;background:oklch(0.12 0.01 60)}
main{overflow:auto;position:relative;min-width:0}
article{max-width:760px;margin:34px auto 60px;padding:56px 64px;background:oklch(0.998 0.002 85);box-shadow:0 2px 24px oklch(0.3 0.01 60/.09);font-family:'Noto Serif SC','Songti SC',serif;font-size:17.5px;line-height:1.95;color:oklch(0.15 0.01 60)}
@media(max-width:1020px){article{margin:0;padding:28px 22px 60px}}
.chhead{padding-bottom:.6em}
.chhead .kicker{font-family:'IBM Plex Mono',monospace;font-size:11.5px;letter-spacing:.14em;color:oklch(0.28 0.01 60)}
.chhead h1{font-size:1.9em;line-height:1.3;margin:.3em 0 .1em;font-weight:700}
.para{margin:0 0 1.15em;text-indent:2em;text-align:justify;position:relative}
.para .pmark{position:absolute;left:-1.6em;top:.55em;font-family:'IBM Plex Mono',monospace;font-size:11px;color:oklch(0.72 0.01 60)}
.para:hover .pmark{color:oklch(0.5 0.12 250)}
.hl{background:oklch(0.89 0.14 92);border-radius:2px;padding:0 1px}
.term{border-bottom:1px dotted oklch(0.62 0.13 250);cursor:help}
.term:hover{background:oklch(0.955 0.03 250)}
.withnote{display:grid;grid-template-columns:minmax(0,1fr);column-gap:40px;align-items:start}
@media(min-width:1180px){.withnote{grid-template-columns:minmax(0,1fr) 236px}}
.entry{margin:1.4em 0 2.4em;padding:24px 26px;background:oklch(0.935 0.035 250);border-radius:10px;font-family:'Noto Sans SC',sans-serif;font-size:14px;line-height:1.8;color:oklch(0.22 0.05 250);display:grid;gap:16px}
.entry .top{display:flex;flex-wrap:wrap;gap:6px 16px;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.06em;color:oklch(0.42 0.15 250)}
.entry h3{margin:0 0 4px;font-size:15.5px;color:oklch(0.26 0.04 250)}
.entry h4{margin:0 0 6px;font-size:13px;color:oklch(0.26 0.04 250)}
.route{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;font-size:13px}
.route span{padding:1px 9px;border-radius:20px;background:oklch(0.97 0.02 250);border:1px solid oklch(0.88 0.04 250)}
.route i{color:oklch(0.45 0.1 250);font-style:normal}
.keys{display:grid;grid-template-columns:22px 1fr;gap:4px 6px;font-size:13.5px}
.keys .k{font-family:'IBM Plex Mono',monospace}
.entry .foot{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px}
.gostart{height:36px;padding:0 16px;border:0;border-radius:8px;background:oklch(0.2 0.06 250);color:oklch(0.98 0.005 250);font-size:13px;cursor:pointer}
.mnote{margin:0 0 1em;padding:12px 13px;background:oklch(0.935 0.035 250);border-radius:8px;font-family:'Noto Sans SC',sans-serif;font-size:12.5px;line-height:1.75;color:oklch(0.22 0.05 250);display:grid;gap:6px;align-self:start}
.mnote .tag{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.06em;color:oklch(0.42 0.16 250)}
.mnote .why{justify-self:start;border:1px solid oklch(0.7 0.08 250);background:oklch(0.97 0.01 250);border-radius:20px;padding:1px 10px;font-size:12px;color:oklch(0.34 0.14 250);cursor:pointer}
.mnote .deep{color:oklch(0.25 0.03 250);padding-top:6px;border-top:1px solid oklch(0.78 0.06 250);display:none}
.mnote.open .deep{display:block}
.quiz{margin:0 0 1.6em;padding:18px 20px;background:oklch(0.935 0.035 250);border-radius:10px;font-family:'Noto Sans SC',sans-serif;font-size:14px;line-height:1.75;color:oklch(0.22 0.05 250);display:grid;gap:10px}
.quiz .tag{font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.06em;color:oklch(0.42 0.15 250)}
.quiz button{border:1px solid oklch(0.82 0.05 250);background:oklch(0.98 0.01 250);border-radius:8px;padding:7px 14px;font-size:13.5px;color:oklch(0.25 0.05 250);cursor:pointer;text-align:left}
.quiz button.ok{background:oklch(0.92 0.09 145);border-color:oklch(0.7 0.12 145)}
.quiz button.no{background:oklch(0.93 0.06 25);border-color:oklch(0.75 0.1 25)}
.quiz .fb{display:none;border-top:1px solid oklch(0.82 0.05 250);padding-top:8px}
.quiz.done .fb{display:block}
.endrow{margin-top:3em;padding-top:1.4em;border-top:1px solid oklch(0.82 0.01 80);display:flex;justify-content:space-between;align-items:baseline;font-size:.85em;color:oklch(0.36 0.012 60)}
figure.bimg{margin:.9em 0 1.8em;text-align:center}
figure.bimg img{max-width:100%;height:auto;border-radius:4px;box-shadow:0 1px 10px oklch(0.3 0.01 60/.13)}
footer{position:relative;display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);gap:10px;align-items:center;padding:0 14px;border-top:1px solid oklch(0.82 0.01 80);background:oklch(0.988 0.003 80);font-size:13px}
footer .prog{position:absolute;top:-1px;left:0;height:2px;width:0;background:oklch(0.12 0.01 60)}
footer button{border:0;background:transparent;font-size:13px;color:oklch(0.18 0.012 60);cursor:pointer;padding:8px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:280px}
.floatcard{position:fixed;z-index:45;padding:14px 16px;background:oklch(0.97 0.02 250);border:1px solid oklch(0.75 0.06 250);border-radius:10px;box-shadow:0 10px 30px oklch(0.3 0.03 250/.14);font-size:13.5px;line-height:1.7;color:oklch(0.22 0.05 250);display:grid;gap:8px;width:300px}
.floatcard .nm{font-family:'Noto Serif SC',serif;font-size:16px;font-weight:600;color:oklch(0.25 0.03 250)}
.floatcard .ai{font-family:'IBM Plex Mono',monospace;font-size:10px;color:oklch(0.42 0.15 250);white-space:nowrap}
.chip{padding:0 7px;border-radius:4px;background:oklch(0.88 0.045 250);font-size:12.5px}
.selpop{position:fixed;z-index:50;transform:translate(-50%,-100%);display:flex;gap:2px;padding:4px;background:oklch(0.26 0.012 60);border-radius:8px;box-shadow:0 8px 24px oklch(0.2 0.01 60/.25)}
.selpop button{border:0;background:transparent;color:oklch(0.95 0.005 80);font-size:13px;padding:6px 10px;border-radius:5px;cursor:pointer}
.selpop button:hover{background:oklch(0.34 0.012 60)}
.selpop .sw{display:inline-block;width:10px;height:10px;border-radius:2px;background:oklch(0.88 0.11 88);margin-right:6px;vertical-align:-1px}
.scrim{position:fixed;inset:0;z-index:60;background:oklch(0.2 0.01 60/.32);display:flex;justify-content:center;align-items:flex-start;padding:9vh 16px 0}
.panel{width:min(660px,100%);max-height:76vh;display:flex;flex-direction:column;background:oklch(0.99 0.004 85);border-radius:12px;box-shadow:0 20px 60px oklch(0.2 0.01 60/.3);overflow:hidden}
.panel input{border:0;outline:none;padding:18px 20px;font-size:16px;background:transparent;color:oklch(0.15 0.01 60);border-bottom:1px solid oklch(0.82 0.01 80);font-family:inherit}
.panel .tabs{display:flex;align-items:center;gap:4px;padding:10px 14px;border-bottom:1px solid oklch(0.92 0.008 80)}
.panel .tabs button{border:0;background:transparent;padding:4px 10px;border-radius:6px;font-size:12.5px;color:oklch(0.36 0.01 60);cursor:pointer}
.panel .tabs button.on{background:oklch(0.9 0.01 80);color:oklch(0.15 0.01 60);font-weight:600}
.panel .results{overflow:auto;padding:8px}
.res{display:block;width:100%;text-align:left;border:0;background:transparent;padding:10px 12px;border-radius:8px;cursor:pointer}
.res:hover{background:oklch(0.955 0.02 250)}
.res .r1{color:oklch(0.28 0.01 60);font-family:'IBM Plex Mono',monospace;font-size:11px}
.res .r2{font-family:'Noto Serif SC',serif;font-size:14px;line-height:1.7}
.res mark{background:oklch(0.89 0.14 92)}
.drawer{position:fixed;z-index:61;top:0;right:0;bottom:0;width:min(420px,92vw);background:oklch(0.988 0.003 80);box-shadow:-10px 0 40px oklch(0.2 0.01 60/.15);display:flex;flex-direction:column}
.drawer .dh{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid oklch(0.82 0.01 80);font-weight:600}
.drawer .db{overflow:auto;padding:16px 18px 24px;display:grid;gap:22px;align-content:start}
.drawer .grouplabel{font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.06em;color:oklch(0.28 0.01 60)}
.empty{font-size:13px;color:oklch(0.28 0.01 60)}
.noteitem{display:grid;gap:8px;padding:12px 14px;background:oklch(0.99 0.004 85);border:1px solid oklch(0.92 0.006 80);border-radius:8px}
.noteitem textarea{width:100%;box-sizing:border-box;resize:vertical;border:1px solid oklch(0.82 0.01 80);border-radius:6px;padding:6px 8px;font-size:13px;color:oklch(0.18 0.012 60);background:oklch(0.98 0.004 85);font-family:'Noto Sans SC',sans-serif}
.linkish{border:0;background:transparent;padding:0;font-size:12px;color:oklch(0.45 0.09 250);cursor:pointer}
.graylink{border:0;background:transparent;padding:0;font-size:12px;color:oklch(0.28 0.01 60);cursor:pointer}
#frame.original .ai-only{display:none!important}
</style>
</head>
<body>
<div id="frame">
  <header>
    <div class="htitle">
      <div class="t1">__TITLE__ <span class="mono" style="font-weight:400;font-size:11px;color:oklch(0.42 0.01 60)">__SUBTITLE__</span></div>
      <div class="t2" id="hsub"></div>
    </div>
    <div style="display:flex;align-items:center;gap:10px">
      <span class="mono" style="font-size:10.5px;color:oklch(0.42 0.01 60);letter-spacing:.06em">LAYER</span>
      <div class="seg" id="modeseg">
        <button data-m="original" title="原文:只有书">Original</button>
        <button data-m="enhanced" title="增强:边注 + 章导读 + 术语卡">Enhanced</button>
        <button data-m="study" title="学习:全部展开 + 自测">Study</button>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:6px">
      <button class="hbtn" id="btnSearch">Search <kbd>Ctrl K</kbd></button>
      <button class="hbtn" id="btnBm" title="书签本章">◇ 书签</button>
      <button class="hbtn" id="btnNotes">Notes <span class="mono" style="font-size:11px" id="hlcount">0</span></button>
    </div>
  </header>
  <div class="bodygrid">
    <nav id="toc"></nav>
    <main id="scroller"><article id="article"></article></main>
  </div>
  <footer>
    <div class="prog" id="fprog"></div>
    <button id="prevBtn" style="justify-self:start">←</button>
    <div class="mono" id="fmid" style="font-size:11.5px;color:oklch(0.36 0.01 60);white-space:nowrap"></div>
    <button id="nextBtn" style="justify-self:end">→</button>
  </footer>
</div>
<script id="imgdata" type="application/json">__IMGDATA__</script>
<script id="bookdata" type="application/json">__DATA__</script>
<script>
"use strict";
const BOOK=JSON.parse(document.getElementById("bookdata").textContent);
const CONCEPTS=BOOK.concepts||[];
const LS="db:"+BOOK.slug+":";
const $=s=>document.querySelector(s);
let state={mode:localStorage.getItem(LS+"mode")||"enhanced",ch:+(localStorage.getItem(LS+"ch")||0),
  bm:new Set(JSON.parse(localStorage.getItem(LS+"bm")||"[]")),
  hls:JSON.parse(localStorage.getItem(LS+"hl")||"[]"),
  scroll:JSON.parse(localStorage.getItem(LS+"scroll")||"{}"),
  fs:+(localStorage.getItem(LS+"fs")||17.5)};
function save(){localStorage.setItem(LS+"mode",state.mode);localStorage.setItem(LS+"ch",state.ch);
  localStorage.setItem(LS+"bm",JSON.stringify([...state.bm]));localStorage.setItem(LS+"hl",JSON.stringify(state.hls));
  localStorage.setItem(LS+"scroll",JSON.stringify(state.scroll));localStorage.setItem(LS+"fs",state.fs);}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const IMGPRE="__IMGPRE__";
let IMG={};try{IMG=JSON.parse(document.getElementById("imgdata").textContent||"{}")}catch(e){}
function imgSrc(e){return IMG[e.src]||(IMGPRE+e.src);}
function figHTML(e){return '<figure class="bimg"><img loading="lazy" src="'+imgSrc(e)+'"'+(e.w?' width="'+e.w+'" height="'+e.h+'"':'')+' alt=""></figure>';}
function markTerms(text){
  let out="",pos=0;const lower=text.toLowerCase();const hits=[];
  for(const c of CONCEPTS){const nm=c.name;let i=0;
    while((i=text.indexOf(nm,i))>-1){hits.push([i,nm,c]);i+=nm.length;}}
  hits.sort((a,b)=>a[0]-b[0]);
  for(const[i,nm,c]of hits){if(i<pos)continue;out+=esc(text.slice(pos,i));
    out+='<span class="term" data-term="'+c.id+'">'+esc(nm)+'</span>';pos=i+nm.length;}
  out+=esc(text.slice(pos));return hits.length?out:esc(text);}
function paraEl(ch,i,p,enh){
  const note=enh?(ch.notes||[]).find(n=>n.at===i):null;
  let inner=enh?markTerms(p):esc(p);
  const hl=state.hls.find(h=>h.ch===ch.idx&&h.p===i);
  let para='<p class="para" id="p-'+ch.idx+'-'+i+'" data-ch="'+ch.idx+'" data-p="'+i+'"><span class="pmark">'+String(i+1)+'</span>'+inner+'</p>';
  if(note){para='<div class="withnote">'+para+'<aside class="mnote ai-only"><span class="tag">AI · '+esc(note.tag)+'</span><span>'+esc(note.text)+'</span>'+
    (note.deeper?'<button class="why" onclick="this.closest(\'.mnote\').classList.toggle(\'open\');event.stopPropagation()">Deeper ▸</button><span class="deep">'+esc(note.deeper)+'</span>':'')+'</aside></div>';}
  return para;}
function renderTOC(){
  const el=$("#toc");let h='<div class="navlabel">CONTENTS · 目录</div>';
  BOOK.chapters.forEach((ch,idx)=>{
    const cur=idx===state.ch,bmd=state.bm.has(idx);
    h+='<button class="toc-ch'+(cur?' active':'')+'" data-i="'+idx+'"><span class="n">'+(idx+1)+'</span><span style="flex:1;text-align:left">'+esc(ch.title)+'</span>'+(ch.entry?'<span class="mono" style="font-size:10px;color:oklch(0.42 0.01 60)">~'+ch.entry.time+'m</span>':'')+(bmd?'<span class="diamond"></span>':'')+'</button>';
    if(cur){h+='<button class="toc-sub" data-goto="p-'+idx+'-0">本章开头 · ¶1</button>';
      const step=ch.paras.length>200?50:12;
      for(let i=step;i<ch.paras.length;i+=step)h+='<button class="toc-sub" data-goto="p-'+idx+'-'+i+'">¶'+(i+1)+'</button>';
      if(ch.entry)h+='<button class="toc-sub" data-goto="ch-entry">章导读 · AI</button>';
      if(ch.quiz)h+='<button class="toc-sub" data-goto="quiz">自测 · AI</button>';}});
  const pct=Math.round((state.ch)/(BOOK.chapters.length-1)*100);
  h+='<div class="toc-foot"><div class="row"><span>BOOK</span><span>'+pct+'%</span></div><div class="bar"><div style="width:'+pct+'%"></div></div><div style="font-size:12px;color:oklch(0.28 0.01 60)">共 '+BOOK.chapters.length+' 章 · '+BOOK.total_paras+' 段</div></div>';
  el.innerHTML=h;
  el.querySelectorAll(".toc-ch").forEach(b=>b.onclick=()=>goto(+b.dataset.i,null));
  el.querySelectorAll(".toc-sub").forEach(b=>b.onclick=()=>{const t=document.getElementById(b.dataset.goto);if(t)t.scrollIntoView({behavior:"smooth"});});}
function render(){
  const ch=BOOK.chapters[state.ch],mode=state.mode,enh=mode!=="original";
  $("#frame").classList.toggle("original",mode==="original");
  document.querySelectorAll("#modeseg button").forEach(b=>b.classList.toggle("on",b.dataset.m===mode));
  $("#hsub").textContent=ch.title+" · 共 "+ch.paras.length+" 段";
  $("#article").style.fontSize=state.fs+"px";
  let h='<div class="chhead"><div class="kicker">CHAPTER '+(state.ch+1)+' / '+BOOK.chapters.length+'</div><h1>'+esc(ch.title)+'</h1></div>';
  const imAfter={};(ch.images||[]).forEach(e=>{(imAfter[e.after]=imAfter[e.after]||[]).push(e);});
  (imAfter[-1]||[]).forEach(e=>{h+=figHTML(e);});
  if(enh&&ch.entry){const e=ch.entry;
    h+='<section class="entry ai-only" id="ch-entry"><div class="top"><span>AI DISTILLED · 本章导读</span><span>≈ '+e.time+' min · '+ch.paras.length+' 段</span></div>'+
    '<div><h3>这一章要回答什么</h3>'+esc(e.q)+'</div>'+
    '<div><h4>Knowledge route · 知识路线</h4><div class="route">'+e.route.map((r,i)=>'<span>'+esc(r)+'</span>'+(i<e.route.length-1?'<i>→</i>':'')).join('')+'</div></div>'+
    '<div><h4>Key points · 关键点</h4><div class="keys">'+e.keys.map((k,i)=>'<span class="k">'+(i+1)+'</span><span>'+esc(k)+'</span>').join('')+'</div></div>'+
    (e.motif?'<div style="font-size:13px"><h4>Theme · 补充</h4>'+esc(e.motif)+'</div>':'')+
    '<div class="foot"><span style="font-size:12px;color:oklch(0.42 0.15 250)">AI 内容与原文隔离 · 虚线词可看概念卡</span><button class="gostart" onclick="document.getElementById(\'p-'+ch.idx+'-0\').scrollIntoView()">开始读原文 ↓</button></div></section>';}
  for(let i=0;i<ch.paras.length;i++){h+=paraEl(ch,i,ch.paras[i],enh);(imAfter[i]||[]).forEach(e=>{h+=figHTML(e);});}
  if(mode==="study"&&ch.quiz){const q=ch.quiz;
    h+='<section class="quiz ai-only" id="quiz"><div class="tag">STUDY · 自测 Self-check</div><div style="font-weight:600">'+esc(q.q)+'</div><div style="display:flex;flex-wrap:wrap;gap:8px">'+
      (Array.isArray(q.a)?q.a.map((a,i)=>'<button data-i="'+i+'">'+esc(a)+'</button>').join(''):'<button data-i="0">'+esc(q.a)+'</button>')+
      '</div><div class="fb">'+esc(q.fb)+'</div></section>';}
  h+='<div class="endrow"><span>'+esc(ch.title)+' · 完</span><span class="mono" style="font-size:12px">'+(state.ch<BOOK.chapters.length-1?"Next · "+esc(BOOK.chapters[state.ch+1].title)+" →":"The End")+'</span></div>';
  $("#article").innerHTML=h;
  document.querySelectorAll(".quiz").forEach(qz=>{qz.querySelectorAll("button").forEach(b=>b.onclick=()=>{
    const q=ch.quiz;if(Array.isArray(q.a)){const ok=+b.dataset.i===q.correct;
      qz.querySelectorAll("button").forEach(x=>{x.disabled=true;if(+x.dataset.i===q.correct)x.classList.add("ok");});
      if(!ok)b.classList.add("no");}
    qz.classList.add("done");});});
  document.querySelectorAll(".term").forEach(t=>{
    t.addEventListener("mouseenter",()=>showConcept(t.dataset.term,t));
    t.addEventListener("mouseleave",hideFloat);
    t.addEventListener("click",()=>showConcept(t.dataset.term,t));});
  $("#prevBtn").textContent=state.ch>0?"← "+BOOK.chapters[state.ch-1].title.slice(0,20):"←";
  $("#nextBtn").textContent=state.ch<BOOK.chapters.length-1?BOOK.chapters[state.ch+1].title.slice(0,20)+" →":"→";
  $("#prevBtn").disabled=state.ch===0;$("#nextBtn").disabled=state.ch>=BOOK.chapters.length-1;
  renderTOC();updateFooter();
  $("#hlcount").textContent=state.hls.length;
  $("#scroller").scrollTop=0;
  if(state.scroll[state.ch])requestAnimationFrame(()=>{$("#scroller").scrollTop=state.scroll[state.ch];});}
function applyHlIn(el,hl){
  const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);const nodes=[];
  while(walker.nextNode())nodes.push(walker.currentNode);
  for(const n of nodes){const idx=n.textContent.indexOf(hl.text);
    if(idx>-1&&n.parentNode.className!=="pmark"){const range=document.createRange();
      range.setStart(n,idx);range.setEnd(n,idx+hl.text.length);
      const span=document.createElement("span");span.className="hl";range.surroundContents(span);return;}}}
function updateFooter(){
  const ch=BOOK.chapters[state.ch],sc=$("#scroller");
  const max=sc.scrollHeight-sc.clientHeight||1;
  const inCh=Math.min(1,sc.scrollTop/Math.max(1,max));
  const bp=((state.ch+inCh)/(BOOK.chapters.length))*100;
  $("#fprog").style.width=bp+"%";
  $("#fmid").textContent=ch.title.slice(0,16)+" · Book "+Math.round(bp)+"%";}
function goto(i,pIdx){state.ch=i;save();render();
  if(pIdx!=null){requestAnimationFrame(()=>{const el=document.getElementById("p-"+i+"-"+pIdx)||document.querySelector(".chhead");if(el)el.scrollIntoView();});}
  renderTOC();}
$("#prevBtn").onclick=()=>state.ch>0&&goto(state.ch-1);
$("#nextBtn").onclick=()=>state.ch<BOOK.chapters.length-1&&goto(state.ch+1);
$("#scroller").addEventListener("scroll",()=>{updateFooter();clearTimeout(window._st);
  window._st=setTimeout(()=>{state.scroll[state.ch]=$("#scroller").scrollTop;save();scrollSpy();},120);});
function scrollSpy(){const sc=$("#scroller");let cur=null;
  document.querySelectorAll("#article .para").forEach(el=>{if(el.offsetTop-sc.scrollTop<sc.clientHeight*0.4)cur=el.dataset.p;});
  document.querySelectorAll(".toc-sub").forEach(b=>b.classList.toggle("cur",b.dataset.goto===("p-"+state.ch+"-"+cur)));}
document.querySelectorAll("#modeseg button").forEach(b=>b.onclick=()=>{state.mode=b.dataset.m;save();render();});
$("#btnBm").onclick=()=>{state.bm.has(state.ch)?state.bm.delete(state.ch):state.bm.add(state.ch);save();renderTOC();drawBmBtn();};
function drawBmBtn(){const on=state.bm.has(state.ch);const b=$("#btnBm");
  b.classList.toggle("bm-on",on);b.textContent=(on?"◆":"◇")+" 书签";}
drawBmBtn();
let selRange=null;
document.addEventListener("mouseup",e=>{if(e.target.closest(".selpop,.floatcard,header,nav,footer,.entry,.mnote,.quiz"))return;
  setTimeout(()=>{const s=window.getSelection();if(!s||s.isCollapsed){const p=$(".selpop");if(p)p.remove();return;}
    const txt=s.toString().trim();if(txt.length<2||txt.length>600){const p=$(".selpop");if(p)p.remove();return;}
    const anchor=s.anchorNode;if(!anchor)return;const pEl=(anchor.nodeType===3?anchor.parentElement:anchor).closest(".para");
    if(!pEl){const p=$(".selpop");if(p)p.remove();return;}
    selRange={ch:+pEl.dataset.ch,p:+pEl.dataset.p,text:txt};
    const r=s.getRangeAt(0).getBoundingClientRect();
    let pop=$(".selpop");if(!pop){pop=document.createElement("div");pop.className="selpop";document.body.appendChild(pop);}
    pop.innerHTML='<button data-k="hl"><span class="sw"></span>Highlight</button><button data-k="note">Note</button><button data-k="copy">Copy</button>';
    pop.style.left=(r.left+r.width/2)+"px";pop.style.top=(r.top-8)+"px";
    pop.querySelectorAll("button").forEach(b=>b.onclick=()=>{
      if(b.dataset.k==="copy"){if(navigator.clipboard)navigator.clipboard.writeText(txt);}
      if(b.dataset.k==="hl"){state.hls.push({id:Date.now(),ch:selRange.ch,p:selRange.p,text:selRange.text,note:""});save();render();}
      if(b.dataset.k==="note"){state.hls.push({id:Date.now(),ch:selRange.ch,p:selRange.p,text:selRange.text,note:" "});save();render();openNotes();}
      pop.remove();window.getSelection().removeAllRanges();});},10);});
function showConcept(id,el){const c=CONCEPTS.find(x=>x.id===id);if(!c)return;hideFloat();
  const d=document.createElement("div");d.className="floatcard";d.id="cfloat";
  d.innerHTML='<div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline"><span class="nm">'+esc(c.name)+' <span class="mono" style="font-size:11.5px;font-weight:400;color:oklch(0.36 0.05 250)">'+esc(c.en||"")+'</span></span><span class="ai">AI · CONCEPT</span></div>'+
   '<div>'+esc(c.one)+'</div>'+
   '<div style="display:flex;gap:8px;font-size:12.5px"><span style="color:oklch(0.36 0.04 250)">首次出现</span><button class="linkish" id="cffirst">第 '+(c.first[0]+1)+' 章 ¶'+(c.first[1]+1)+'</button></div>'+
   '<div style="display:flex;flex-wrap:wrap;gap:6px;font-size:12.5px"><span style="color:oklch(0.36 0.04 250)">Related</span>'+c.rel.map(r=>'<span class="chip">'+esc(r)+'</span>').join('')+'</div>';
  document.body.appendChild(d);
  const r=el.getBoundingClientRect();
  let x=Math.min(r.left,innerWidth-320),y=r.bottom+8;
  if(y+d.offsetHeight>innerHeight-10)y=r.top-d.offsetHeight-8;
  d.style.left=Math.max(8,x)+"px";d.style.top=Math.max(8,y)+"px";
  d.addEventListener("mouseleave",hideFloat);
  d.querySelector("#cffirst").onclick=()=>{goto(c.first[0],c.first[1]);hideFloat();};}
function hideFloat(){const f=document.getElementById("cfloat");if(f)f.remove();}
let stab="exact";
function openSearch(){let sc=$(".scrim");if(sc)sc.remove();
  sc=document.createElement("div");sc.className="scrim";
  sc.innerHTML='<div class="panel" onclick="event.stopPropagation()"><input id="q" placeholder="Search · 搜索全文…"><div class="tabs"><button data-s="exact" class="on">Exact · 原文</button><button data-s="concept">Concept · 概念</button><span class="mono" style="margin-left:auto;font-size:11px;color:oklch(0.28 0.01 60)" id="rc"></span></div><div class="results" id="res"></div></div>';
  document.body.appendChild(sc);
  sc.onclick=e=>{if(e.target===sc)sc.remove();};
  const inp=sc.querySelector("#q");inp.focus();
  inp.onkeydown=e=>{if(e.key==="Escape")sc.remove();};
  inp.oninput=()=>runSearch(inp.value,sc);
  sc.querySelectorAll(".tabs button").forEach(b=>b.onclick=()=>{stab=b.dataset.s;
    sc.querySelectorAll(".tabs button").forEach(x=>x.classList.toggle("on",x===b));runSearch(inp.value,sc);});}
function runSearch(q,sc){const res=sc.querySelector("#res"),rc=sc.querySelector("#rc");
  if(!q.trim()){res.innerHTML='<div class="empty" style="padding:10px">输入以搜索全文'+(stab==="concept"?"或概念库":"")+'。</div>';rc.textContent="";return;}
  let html="";let n=0;
  if(stab==="exact"){const needle=q.trim();const low=needle.toLowerCase();
    BOOK.chapters.forEach((ch,idx)=>{ch.paras.forEach((p,i)=>{
      const li=p.toLowerCase().indexOf(low);
      if(li>-1&&n<80){n++;const s=Math.max(0,li-30);
        html+='<button class="res" data-ch="'+idx+'" data-p="'+i+'"><div class="r1">第'+(idx+1)+'章 '+esc(ch.title)+' · ¶'+(i+1)+'</div><div class="r2">…'+esc(p.slice(s,li))+'<mark>'+esc(p.substr(li,needle.length))+'</mark>'+esc(p.slice(li+needle.length,li+needle.length+60))+'…</div></button>';}});
    });}
  else{const needle=q.trim().toLowerCase();
    CONCEPTS.forEach(c=>{if((c.name+(c.en||"")+c.one+c.rel.join("")).toLowerCase().includes(needle)&&n<40){n++;
      html+='<button class="res" data-ch="'+c.first[0]+'" data-p="'+c.first[1]+'"><div class="r1">CONCEPT · '+esc(c.name)+' '+esc(c.en||"")+'</div><div class="r2">'+esc(c.one)+'</div></button>';}});}
  rc.textContent=n+" results";res.innerHTML=html||'<div class="empty" style="padding:10px">无结果。</div>';
  res.querySelectorAll(".res").forEach(b=>b.onclick=()=>{sc.remove();goto(+b.dataset.ch,+b.dataset.p);});}
$("#btnSearch").onclick=openSearch;
document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();openSearch();}
  if(e.key==="Escape"){const s=$(".scrim");if(s)s.remove();const p=$(".selpop");if(p)p.remove();hideFloat();}});
function openNotes(){let d=$(".drawer");if(d){d.remove();return;}
  d=document.createElement("div");d.className="drawer";
  let bmh="";[...state.bm].sort((a,b)=>a-b).forEach(i=>{const ch=BOOK.chapters[i];
    bmh+='<div style="display:flex;align-items:center;gap:10px"><span style="width:7px;height:7px;background:oklch(0.62 0.13 60);transform:rotate(45deg)"></span><button class="linkish" style="flex:1;text-align:left;font-size:13.5px;color:oklch(0.18 0.012 60)" data-goto="'+i+'">'+esc(ch.title)+'</button><button class="graylink" data-delbm="'+i+'">Remove</button></div>';});
  let hlh="";state.hls.forEach(hl=>{const ch=BOOK.chapters.find(c=>c.idx===hl.ch)||{title:""};
    hlh+='<div class="noteitem"><div style="font-family:\'Noto Serif SC\',serif;font-size:14px;line-height:1.7"><span class="hl">'+esc(hl.text)+'</span></div>'+
     '<textarea data-hl="'+hl.id+'" placeholder="Add a note…">'+esc(hl.note===" "?"":hl.note||"")+'</textarea>'+
     '<div style="display:flex;gap:12px;font-family:\'IBM Plex Mono\',monospace;font-size:11px;color:oklch(0.28 0.01 60)"><span style="flex:1">'+esc(ch.title.slice(0,14))+' · ¶'+(hl.p+1)+'</span><button class="linkish" data-loc="'+hl.id+'">Locate</button><button class="graylink" data-del="'+hl.id+'">Delete</button></div></div>';});
  d.innerHTML='<div class="dh"><span>My Notes · 我的标注</span><button class="graylink" style="font-size:18px" id="closeNotes">×</button></div><div class="db">'+
   '<div style="display:grid;gap:8px"><div class="grouplabel">BOOKMARKS</div>'+(bmh||'<div class="empty">点顶栏 ◇ 为当前章加书签。</div>')+'</div>'+
   '<div style="display:grid;gap:12px"><div class="grouplabel">HIGHLIGHTS & NOTES</div>'+(hlh||'<div class="empty">在正文中选中文字即可高亮或记笔记。只保存在本机。</div>')+'</div></div>';
  document.body.appendChild(d);
  d.querySelector("#closeNotes").onclick=()=>d.remove();
  d.querySelectorAll("[data-goto]").forEach(b=>b.onclick=()=>{d.remove();goto(+b.dataset.goto);});
  d.querySelectorAll("[data-delbm]").forEach(b=>b.onclick=()=>{state.bm.delete(+b.dataset.delbm);save();d.remove();openNotes();drawBmBtn();renderTOC();});
  d.querySelectorAll("[data-loc]").forEach(b=>b.onclick=()=>{const hl=state.hls.find(x=>x.id==+b.dataset.loc);d.remove();
    goto(hl.ch,hl.p);});
  d.querySelectorAll("[data-del]").forEach(b=>b.onclick=()=>{state.hls=state.hls.filter(x=>x.id!=+b.dataset.del);save();d.remove();openNotes();render();});
  d.querySelectorAll("textarea").forEach(t=>t.oninput=()=>{const hl=state.hls.find(x=>x.id==+t.dataset.hl);if(hl){hl.note=t.value;save();$("#hlcount").textContent=state.hls.length;}});}
$("#btnNotes").onclick=openNotes;
state.ch=Math.min(state.ch,BOOK.chapters.length-1);
render();
</script>
</body>
</html>
"""

def main():
    chapters_ir = book["chapters"]
    entry = D.get("entry", {}); notes = D.get("notes", {}); quiz = D.get("quiz", {})
    chapters = []
    for i, c in enumerate(chapters_ir):
        chapters.append({
            "idx": i, "title": c["title"], "paras": c["paras"],
            "entry": entry.get(str(i)), "quiz": quiz.get(str(i)),
            "images": c.get("images"),
            "notes": [{"at": n[0], "tag": n[1], "text": n[2], "deeper": (n[3] if len(n) > 3 and n[3] else "")}
                      for n in notes.get(str(i), [])],
        })
    slug = book.get("slug", os.path.basename(out_path))
    # ---- 图片交付:总字节≤2MB 内联 base64,否则复制到 assets/<slug>/ ----
    img_entries = [e for c in chapters for e in (c.get("images") or [])]
    total_img = sum(e.get("bytes") or 0 for e in img_entries)
    img_prefix, imgmap = "", {}
    if img_entries and total_img <= 2 * 1024 * 1024:
        import base64
        for e in img_entries:
            p = os.path.join(ir_dir, e["src"].replace("/", os.sep))
            if os.path.exists(p):
                ext = os.path.splitext(e["src"])[1].lower().lstrip(".") or "jpeg"
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                        "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml"}.get(ext, "image/jpeg")
                imgmap[e["src"]] = f"data:{mime};base64," + base64.b64encode(open(p, "rb").read()).decode()
    elif img_entries:
        import shutil
        ssan = re.sub(r'[\\/:*?"<>|]', "", slug)[:60]
        adir = os.path.join(os.path.dirname(out_path), "assets", ssan, "img")
        os.makedirs(adir, exist_ok=True)
        for e in img_entries:
            p = os.path.join(ir_dir, e["src"].replace("/", os.sep))
            if os.path.exists(p):
                dst = os.path.join(adir, os.path.basename(e["src"]))
                if not os.path.exists(dst):
                    shutil.copyfile(p, dst)
        img_prefix = f"assets/{ssan}/"
    BOOK = {
        "slug": slug,
        "title": sys.argv[4] if len(sys.argv) > 4 else book["title"],
        "subtitle": D.get("subtitle", ""),
        "total_paras": book.get("total_paras", sum(len(c["paras"]) for c in chapters_ir)),
        "chapters": chapters,
        "concepts": D.get("concepts", []),
    }
    data = json.dumps(BOOK, ensure_ascii=False)
    imgdata_js = json.dumps(imgmap, ensure_ascii=False).replace("</", "<\\/")
    html_out = (TEMPLATE
                .replace("__DATA__", data.replace("</", "<\\/"))
                .replace("__IMGDATA__", imgdata_js)
                .replace("__IMGPRE__", img_prefix)
                .replace("__TITLE__", BOOK["title"]).replace("__SUBTITLE__", BOOK["subtitle"]))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    io.open(out_path, "w", encoding="utf-8").write(html_out)
    print("written:", out_path, len(html_out), "bytes,", len(img_entries), "imgs,", "inline" if imgmap else ("assets" if img_entries else "none"))

def list2(x): return x
main()
