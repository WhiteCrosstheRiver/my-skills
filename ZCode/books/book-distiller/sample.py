import json,sys
idx=sys.argv[1]
targets=sys.argv[2] if len(sys.argv)>2 else ""
b=json.load(open(rf"batch\ir\{idx}\book.json",encoding="utf-8"))
print("TITLE:",b["title"],"chapters:",len(b["chapters"]),"paras:",b["total_paras"])
for ci,ch in enumerate(b["chapters"]):
    p=ch["paras"]
    print(f"\n== ch{ci} [{len(p)}paras] {ch['title'][:60]}")
    for pi in [0,1]:
        if pi<len(p): print(f"  p{pi}:",str(p[pi])[:100].replace("\n"," "))
    if targets=="full":
        for pi in {len(p)//3,len(p)*2//3,len(p)-1}:
            if 0<=pi<len(p) and pi>1: print(f"  p{pi}:",str(p[pi])[:100].replace("\n"," "))
