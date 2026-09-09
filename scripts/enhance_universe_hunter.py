from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=ROOT/"share"/"grail-personal-hunter.html"


def main() -> int:
    catalog_path=ROOT/"data"/"universe_catalog.next.json"
    if not catalog_path.exists(): catalog_path=ROOT/"data"/"universe_catalog.json"
    catalog=json.loads(catalog_path.read_text(encoding="utf-8"))
    counts=catalog.get("counts",{})
    page=HTML.read_text(encoding="utf-8")

    badge=f'''<section id="universeCoverage" style="margin:18px 0;padding:14px 16px;border:1px solid #292e3a;border-radius:14px;background:#0d1016;display:flex;gap:18px;align-items:center;flex-wrap:wrap"><b style="color:#e2c06e">UNIVERSE v0.8</b><span>{counts.get('assets',0)} assets</span><span>{counts.get('comics',0)} comics</span><span>{counts.get('collectibles',0)} collectibles</span><span style="color:#737b8c;font-size:11px">catalog → triage → deep scan → Hunter</span></section><div id="kindFilter" style="display:flex;gap:7px;margin:0 0 18px"><button data-kind="all" class="universeKind active">All</button><button data-kind="comic" class="universeKind">Comics</button><button data-kind="collectible" class="universeKind">Collectibles</button></div>'''
    marker='<section id="grid" class="grid">'
    if marker in page and 'id="universeCoverage"' not in page:
        page=page.replace(marker,badge+marker,1)

    css='''<style>.universeKind{border:1px solid #303644;background:#0d1016;color:#aeb6c3;padding:8px 12px;border-radius:99px;font-weight:700;cursor:pointer}.universeKind.active{border-color:#d9b867;color:#e2c06e;background:#1a1811}.kindBadge{border-color:#3a4050!important;color:#9ba5b6!important}</style>'''
    page=page.replace('</head>',css+'</head>',1)

    js=r'''<script>(function(){let kind='all';if(typeof score==='function'){const baseScore=score;score=function(r,p){if(kind!=='all'&&String(r.asset_kind||'collectible')!==kind)return null;return baseScore(r,p)}}if(typeof card==='function'){const baseCard=card;card=function(r,i){let h=baseCard(r,i),k=String(r.asset_kind||'collectible').toUpperCase();return h.replace('<div class="badges">','<div class="badges"><span class="kindBadge">'+k+'</span>')}}document.querySelectorAll('.universeKind').forEach(b=>b.addEventListener('click',()=>{kind=b.dataset.kind;document.querySelectorAll('.universeKind').forEach(x=>x.classList.toggle('active',x===b));if(typeof render==='function')render()}));})();</script>'''
    page=page.replace('</body>',js+'</body>',1)
    HTML.write_text(page,encoding="utf-8")
    print(json.dumps({"enhanced":True,"counts":counts,"filters":["all","comic","collectible"]},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
