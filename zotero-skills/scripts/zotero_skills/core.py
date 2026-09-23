"""Durable state, validated MCP transport and small Zotero primitives."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import ssl
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx
import truststore


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def digest(value):
    if not isinstance(value, bytes):
        value = str(value).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, path)


def default_output():
    return Path(os.environ.get("ZOTERO_SKILLS_OUTPUT", str(Path.home() / "Documents" / "ZoteroSkills")))


class BusyError(RuntimeError):
    pass


@contextlib.contextmanager
def lock(path):
    """OS-released lock: a killed process never leaves a permanent busy flag."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as file:
        file.seek(0)
        if os.name == "nt":
            import msvcrt
            if path.stat().st_size == 0:
                file.write(b"0")
                file.flush()
            file.seek(0)
            try:
                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise BusyError(f"Another job owns {path}") from exc
            try:
                yield
            finally:
                file.seek(0)
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise BusyError(f"Another job owns {path}") from exc
            try:
                yield
            finally:
                fcntl.flock(file, fcntl.LOCK_UN)


class Run:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.state = read_json(self.path / "run.json")

    @classmethod
    def create(cls, output, mode, config):
        path = Path(output) / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + mode + "-" + uuid.uuid4().hex[:6])
        write_json(path / "run.json", {"schema": 1, "mode": mode, "created_at": now(), "updated_at": now(), "config": config, "status": "created", "papers": [], "events": []})
        return cls(path)

    def save(self):
        self.state["updated_at"] = now()
        write_json(self.path / "run.json", self.state)

    def event(self, kind, **details):
        self.state["events"].append({"at": now(), "kind": kind, **details})
        self.save()

    def paper_dir(self, paper):
        ident = paper.get("id") or digest(paper.get("doi") or paper.get("arxiv") or paper["title"])[:20]
        paper["id"] = ident
        path = self.path / "papers" / ident
        path.mkdir(parents=True, exist_ok=True)
        return path


def load_token():
    """Secrets stay local, are never included in diagnostics or persisted manifests."""
    if os.environ.get("ZOTERO_MCP_TOKEN"):
        return os.environ["ZOTERO_MCP_TOKEN"]
    cfg = Path.home() / ".codex" / "config.toml"
    if cfg.exists():
        import tomllib
        servers = tomllib.loads(cfg.read_text(encoding="utf-8")).get("mcp_servers", {})
        for name, server in servers.items():
            if name == "zotero-mcp":
                headers = server.get("http_headers", {})
                auth = headers.get("Authorization", headers.get("authorization", ""))
                if auth.startswith("Bearer "):
                    return auth[7:]
                env = server.get("bearer_token_env_var")
                if env and os.environ.get(env):
                    return os.environ[env]
    roots = []
    if os.environ.get("APPDATA"):
        roots.append(Path(os.environ["APPDATA"]) / "Zotero" / "Zotero" / "Profiles")
    roots.extend([Path.home() / ".zotero" / "zotero", Path.home() / "Library" / "Application Support" / "Zotero" / "Profiles"])
    tokens = set()
    for root in roots:
        for prefs in root.glob("*/prefs.js"):
            for line in prefs.read_text(encoding="utf-8").splitlines():
                match = re.fullmatch(r'user_pref\("extensions\.zotero\.zotero-agent\.auth\.token",\s*("(?:[^"\\]|\\.)*")\);', line)
                if match:
                    tokens.add(json.loads(match.group(1)))
    if len(tokens) == 1:
        return tokens.pop()
    raise RuntimeError("Set ZOTERO_MCP_TOKEN (no token or multiple Zotero profiles found).")


class MCP:
    def __init__(self, url=None, token=None):
        self.url = url or os.environ.get("ZOTERO_MCP_URL", "http://127.0.0.1:23120/mcp")
        self.client = httpx.Client(timeout=125, trust_env=False, headers={"Authorization": "Bearer " + (token or load_token()), "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
        self.index = 0
        init = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "zotero-skills", "version": "0.1.0"}})
        self.client.headers["MCP-Protocol-Version"] = init.get("protocolVersion", "2025-06-18")
        self.client.post(self.url, json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}).raise_for_status()
        self.tools = {t["name"]: t for t in self.rpc("tools/list", {}).get("tools", [])}

    def rpc(self, method, params):
        self.index += 1
        # Never retry a POST blindly: timeouts can follow a committed write.
        response = self.client.post(self.url, json={"jsonrpc": "2.0", "id": self.index, "method": method, "params": params})
        response.raise_for_status()
        if response.headers.get("Mcp-Session-Id"):
            self.client.headers["Mcp-Session-Id"] = response.headers["Mcp-Session-Id"]
        if "text/event-stream" in response.headers.get("Content-Type", ""):
            payloads = [json.loads(line[5:].strip()) for line in response.text.splitlines() if line.startswith("data:") and line[5:].strip()]
            result = next((p for p in payloads if p.get("id") == self.index), None)
            if result is None:
                raise RuntimeError("MCP stream contained no matching response")
        else:
            result = response.json()
        if "error" in result:
            raise RuntimeError(str(result["error"]))
        return result.get("result", {})

    def call(self, name, **arguments):
        if name not in self.tools:
            raise RuntimeError(f"MCP capability missing: {name}. Check Zotero Agent settings.")
        result = self.rpc("tools/call", {"name": name, "arguments": arguments})
        content = "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if result.get("isError"):
            raise RuntimeError(content)
        try:
            decoded = json.loads(content)
        except ValueError:
            decoded = content
        if isinstance(decoded, dict) and (decoded.get("error") or decoded.get("success") is False):
            raise RuntimeError(str(decoded))
        return decoded

    def js(self, code, **params):
        prefix = "const P = " + json.dumps(params, ensure_ascii=True) + ";\n"
        value = self.call("run_javascript", code=prefix + code, timeout_ms=120000)
        if not isinstance(value, dict) or value.get("error"):
            raise RuntimeError(str(value))
        return value.get("result")

    def doctor(self):
        required = ["get_content", "write_note", "write_item", "run_javascript", "create_collection"]
        runtime = self.js("return {version:Zotero.version, libraryID:Zotero.Libraries.userLibraryID, write:Zotero.Prefs.get('extensions.zotero.zotero-agent.write.enabled',true), eval:Zotero.Prefs.get('extensions.zotero.zotero-agent.eval.enabled',true)};")
        return {"runtime": runtime, "missing": [x for x in required if x not in self.tools], "available_tools": len(self.tools), "credentials": "local; redacted"}

    def ensure_collection(self, name, library=1, parent=None):
        return self.js("""
const all=Zotero.Collections.getByLibrary(P.library,true);
const hit=all.find(c=>c.name===P.name && (c.parentKey||null)===(P.parent||null));
if(hit) return hit.key;
const lib=Zotero.Libraries.get(P.library); if(!lib || !lib.editable) throw new Error('Library not editable');
const c=new Zotero.Collection(); c.libraryID=P.library; c.name=P.name;
if(P.parent)c.parentKey=P.parent; await c.saveTx(); return c.key;
""", name=name, library=library, parent=parent)

    def snapshot(self, key, library=1):
        return self.js("""
const x=await Zotero.Items.getByLibraryAndKeyAsync(P.library,P.key);
if(!x || x.deleted) throw new Error('Item missing or trashed: '+P.key);
return {item:x.toJSON(), notes: await Promise.all(x.isRegularItem()?x.getNotes().map(async id=>{const n=await Zotero.Items.getAsync(id);return {key:n.key,html:n.getNote(),tags:n.getTags()}}):[]), attachments:await Promise.all(x.isRegularItem()?x.getAttachments().map(async id=>{const a=await Zotero.Items.getAsync(id);return {key:a.key,title:a.getField('title'),contentType:a.attachmentContentType,path:await a.getFilePathAsync(),url:a.getField('url'),annotations:a.isPDFAttachment()?a.getAnnotations().map(n=>n.toJSON()):[]}}):[])};
""", key=key, library=library)

    def import_paper(self, paper, collection, library=1):
        # Marker recovers a timed-out create even for items without a DOI.
        result = self.js(r"""
const coll=await Zotero.Collections.getByLibraryAndKeyAsync(P.library,P.collection);
if(!coll)throw new Error('Target collection missing');
const marker='zotero-skills:source:'+P.identity;
const s=new Zotero.Search();s.libraryID=P.library;s.addCondition('itemType','isNot','attachment');s.addCondition('itemType','isNot','note');
const ids=await s.search(); const items=await Zotero.Items.getAsync(ids);
const doi=v=>String(v||'').trim().toLowerCase().replace(/^https?:\/\/(dx\.)?doi\.org\//,'').replace(/^doi:\s*/,'');
const norm=v=>String(v||'').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
let x=items.find(i=>!i.deleted&&((P.paper.doi&&doi(i.getField('DOI'))===doi(P.paper.doi))||i.hasTag(marker)||(P.paper.arxiv&&i.getField('url').includes('arxiv.org/abs/'+P.paper.arxiv))));
if(!x) x=items.find(i=>!i.deleted&&norm(i.getField('title'))===norm(P.paper.title)&&String(i.getField('date')).slice(0,4)===String(P.paper.year||'').slice(0,4)&&(!P.paper.authors?.length||norm(JSON.stringify(i.getCreators())).includes(norm(P.paper.authors[0].split(' ').at(-1)))));
let created=false;
await Zotero.DB.executeTransaction(async()=>{
if(!x){x=new Zotero.Item('journalArticle');x.libraryID=P.library;x.setField('title',P.paper.title);if(P.paper.doi)x.setField('DOI',P.paper.doi);if(P.paper.year)x.setField('date',String(P.paper.year));if(P.paper.abstract)x.setField('abstractNote',P.paper.abstract);if(P.paper.url)x.setField('url',P.paper.url);if(P.paper.venue)x.setField('publicationTitle',P.paper.venue);x.setCreators((P.paper.authors||[]).map(name=>({name,creatorType:'author'})));x.addTag(marker);created=true;}
x.addToCollection(coll.id);await x.save();});return {itemKey:x.key,created};
""", paper=paper, identity=digest(paper.get("doi") or paper.get("arxiv") or paper["title"])[:24], collection=collection, library=library)
        return result

    def attach(self, key, path, title, library=1):
        content_hash = digest(Path(path).read_bytes())
        # Covers a crash after importFromFile committed but before its tag was saved.
        for attachment in self.snapshot(key, library)["attachments"]:
            existing = attachment.get("path")
            if existing and Path(existing).is_file() and digest(Path(existing).read_bytes()) == content_hash:
                return {"key": attachment["key"], "reused": True}
        return self.js("""
const item=await Zotero.Items.getByLibraryAndKeyAsync(P.library,P.key);if(!item||item.deleted)throw new Error('Parent missing');
const marker='zotero-skills:file:'+P.sha;
for(const id of item.getAttachments()){const a=await Zotero.Items.getAsync(id);if(a.hasTag(marker))return {key:a.key,reused:true};}
const a=await Zotero.Attachments.importFromFile({file:P.path,parentItemID:item.id,title:P.title});a.addTag(marker);await a.saveTx();return {key:a.key,reused:false};
""", key=key, path=str(Path(path).resolve()), title=title, sha=content_hash, library=library)


class Network:
    """GET-only retries; use the OS certificate store, including corporate roots."""
    def __init__(self, cache):
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT), timeout=45, follow_redirects=True, headers={"User-Agent": "zotero-skills/0.1 (+https://github.com/WhiteCrosstheRiver/my-skills)", "Accept-Encoding": "gzip, deflate"})
        self.last = {}

    def get(self, url, params=None, json_data=True, cache=True, headers=None):
        ident = digest(json.dumps([url, params], sort_keys=True))
        path = self.cache / (ident + (".json" if json_data else ".bin"))
        if cache and path.exists() and time.time() - path.stat().st_mtime < 86400:
            return read_json(path) if json_data else path.read_bytes()
        host = httpx.URL(url).host
        delay = 3.1 if host.endswith("arxiv.org") else 1.1
        for attempt in range(4):
            time.sleep(max(0, delay - (time.monotonic() - self.last.get(host, 0))))
            self.last[host] = time.monotonic()
            try:
                response = self.client.get(url, params=params, headers=headers)
                if response.status_code == 406 and host.endswith("arxiv.org"):
                    # Some arXiv edges reject the httpx request representation. The
                    # stdlib's standard GET is accepted; retain OS TLS validation.
                    import urllib.parse
                    import urllib.request
                    full_url = url + (("&" if "?" in url else "?") + urllib.parse.urlencode(params) if params else "")
                    time.sleep(delay)
                    request = urllib.request.Request(full_url, headers={"Accept-Encoding": "identity"})
                    with urllib.request.urlopen(request, context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT), timeout=45) as alt:
                        response = httpx.Response(alt.status, content=alt.read(), headers=dict(alt.headers), request=response.request)
                if response.status_code in [429, 500, 502, 503, 504] and attempt < 3:
                    wait = response.headers.get("Retry-After", "")
                    time.sleep(min(float(wait) if wait.isdigit() else 2 ** (attempt + 1), 45))
                    continue
                response.raise_for_status()
                value = response.json() if json_data else response.content
                if cache:
                    if json_data:
                        write_json(path, value)
                    else:
                        path.write_bytes(value)
                return value
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("GET retry budget exhausted")
