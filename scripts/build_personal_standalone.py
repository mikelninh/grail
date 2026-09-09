from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUT = ROOT / "share" / "grail-personal-hunter.html"


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def eligible(rows: list[dict]) -> list[dict]:
    return [
        r for r in rows
        if r.get("live_status") == "live"
        and r.get("signal_class") in {"GRAIL", "EDGE", "WATCH"}
        and r.get("actionability") != "reject-price"
    ]


def global_score(r: dict) -> float:
    score = float(r.get("opportunity_score") or 0)
    score += 15 if r.get("signal_class") == "GRAIL" else 5 if r.get("signal_class") == "EDGE" else 0
    score += min(10, max(0, -float(r.get("premium_to_floor_pct") or 0)) / 8)
    score += 6 if float(r.get("mint_score") or 0) >= 75 else 3 if float(r.get("mint_score") or 0) >= 45 else 0
    return score


def choose(rows: list[dict], limit: int = 3) -> list[dict]:
    rows = sorted(eligible(rows), key=global_score, reverse=True)
    out: list[dict] = []
    seen: set[str] = set()
    cats: dict[str, int] = {}
    for r in rows:
        src = str(r.get("source_url") or "")
        cat = str(r.get("category") or "Other")
        if src in seen or cats.get(cat, 0) >= 2:
            continue
        out.append(r)
        seen.add(src)
        cats[cat] = cats.get(cat, 0) + 1
        if len(out) == limit:
            break
    return out


def fallback_card(r: dict, idx: int) -> str:
    gap = float(r.get("premium_to_floor_pct") or 0)
    image = f'<img src="{esc(r.get("image_url"))}" alt="" loading="lazy">' if r.get("image_url") else ""
    links: list[str] = []
    if r.get("stackr_url"):
        links.append(f'<a class="primary" href="{esc(r["stackr_url"])}" target="_blank" rel="noopener">Open StackR ↗</a>')
    if r.get("veve_url"):
        links.append(f'<a href="{esc(r["veve_url"])}" target="_blank" rel="noopener">VeVe ↗</a>')
    links.append(f'<a href="{esc(r.get("source_url"))}" target="_blank" rel="noopener">Evidence ↗</a>')
    reason = (r.get("reasons") or [r.get("why") or "Market signal"])[0]
    key = f"{r.get('source_url')}#{r.get('mint')}"
    return f'''<article class="card" data-key="{esc(key)}">
      <div class="rank">0{idx}</div><div class="media">{image}<span>{esc(r.get('signal_class'))}</span></div>
      <div class="body"><div class="meta"><span>{esc(r.get('category'))}</span><b>{round(float(r.get('confidence') or 0))}% evidence</b></div>
      <h3>{esc(r.get('collectible'))}</h3><div class="mint">Edition #{esc(r.get('mint'))} <small>Mint {round(float(r.get('mint_score') or 0))}/100</small></div>
      <div class="prices"><div><small>ASK</small><b>${float(r.get('ask_usd') or 0):,.2f}</b></div><div><small>FLOOR*</small><b>${float(r.get('floor_usd') or 0):,.2f}</b></div><div><small>POSITION</small><b>{gap:+.1f}%</b></div></div>
      <p class="personalWhy">{esc(reason)}</p><div class="badges"><span>● LIVE</span><span>{esc(r.get('signal_class'))}</span></div>
      <div class="actions">{''.join(links)}</div></div></article>'''


def main() -> int:
    payload = json.loads((SITE / "data" / "opportunities.json").read_text(encoding="utf-8"))
    rows = eligible(payload.get("candidates", []))
    picks = choose(rows)
    counts = payload.get("counts", {})
    categories = sorted({str(r.get("category")) for r in rows if r.get("category")})
    embedded = json.dumps(rows, separators=(",", ":")).replace("</", "<\\/")
    category_options = "".join(
        f'<label><input type="checkbox" name="cat" value="{esc(c)}"> {esc(c)}</label>' for c in categories
    )
    fallback = "".join(fallback_card(r, i) for i, r in enumerate(picks, 1))
    top = round(global_score(picks[0])) if picks else "—"

    css = r'''*{box-sizing:border-box}body{margin:0;background:#090a0f;color:#f4f1e8;font-family:Inter,system-ui,sans-serif}main{max-width:1320px;margin:auto;padding:28px}h1,h2,h3{font-family:Georgia,serif;font-weight:400}.hero{padding:60px 0 30px;border-bottom:1px solid #282d39}.eyebrow{letter-spacing:.18em;color:#d9b867;font-size:10px;font-weight:800}.hero h1{font-size:clamp(48px,7vw,92px);line-height:.96;margin:12px 0}.hero p{max-width:820px;color:#9da5b3;line-height:1.6}.metrics{display:grid;grid-template-columns:repeat(4,1fr);margin:24px 0;border:1px solid #292e3a;border-radius:16px;overflow:hidden}.metrics div{padding:18px;border-right:1px solid #292e3a}.metrics div:last-child{border:0}.metrics small{display:block;color:#788092;font-size:9px}.metrics b{font-size:28px}.personal{border:1px solid #332f28;background:#111319;padding:20px;border-radius:16px;margin:24px 0}.personal-head{display:flex;justify-content:space-between;gap:20px;align-items:center}.personal h2{margin:0}.controls{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}.field{display:flex;flex-direction:column;gap:7px}.field>label{font-size:10px;color:#8e96a6;text-transform:uppercase;letter-spacing:.1em}.field input[type=number],.field input[type=text],.field textarea{background:#0c0f15;color:#eee;border:1px solid #303644;border-radius:9px;padding:10px}.cats,.mints{display:flex;flex-wrap:wrap;gap:8px}.cats label,.mints label{border:1px solid #303644;padding:7px 9px;border-radius:99px;font-size:10px;color:#aeb6c3}.buttons{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}.buttons button,.fileButton{border:1px solid #d9b867;background:#d9b867;color:#111;padding:10px 14px;border-radius:9px;font:700 12px Inter,system-ui;cursor:pointer}.buttons .secondary,.fileButton.secondary{background:transparent;color:#ccc;border-color:#303644}.privacy{font-size:10px;color:#697182;margin-top:10px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.card{position:relative;overflow:hidden;background:#11141b;border:1px solid #292e3a;border-radius:18px}.rank{position:absolute;z-index:2;top:12px;left:12px;font-size:10px;color:#e2c06e}.media{height:220px;position:relative;background:#171a22}.media img{width:100%;height:100%;object-fit:cover}.media span{position:absolute;bottom:10px;left:12px;background:#090b10cc;border:1px solid #554b32;color:#e2c06e;border-radius:99px;padding:5px 8px;font-size:9px}.body{padding:16px}.meta{display:flex;justify-content:space-between;color:#798192;font-size:9px;text-transform:uppercase}.body h3{font-size:22px;margin:9px 0}.mint{font-weight:800}.mint small{color:#d9b867}.prices{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin:13px 0}.prices div{background:#0b0e13;padding:9px;border-radius:8px}.prices small{display:block;color:#6f7787;font-size:8px}.personalWhy{min-height:55px;color:#a5acba;font-size:12px;line-height:1.5}.badges{display:flex;gap:5px;flex-wrap:wrap}.badges span{border:1px solid #303644;border-radius:99px;padding:4px 7px;font-size:8px}.actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:12px}.actions a,.actions button{padding:10px;border:1px solid #303644;border-radius:8px;text-align:center;color:#ddd;text-decoration:none;font:600 10px Inter,system-ui;background:transparent;cursor:pointer}.actions .primary{grid-column:1/-1;background:#eee7d5;color:#111;border-color:#eee7d5;font-weight:800}.actions .active{border-color:#d9b867;color:#e2c06e;background:#1a1811}.status{color:#d9b867;font-size:11px}.empty{grid-column:1/-1;padding:50px;border:1px dashed #303644;border-radius:14px;text-align:center;color:#8d95a4}.toast{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);background:#171a22;border:1px solid #353b49;padding:10px 14px;border-radius:9px;opacity:0;transition:.2s;pointer-events:none}.toast.show{opacity:1}@media(max-width:900px){.grid{grid-template-columns:1fr}.controls{grid-template-columns:1fr}.metrics{grid-template-columns:1fr 1fr}.personal-head{align-items:flex-start;flex-direction:column}}'''

    js = r'''const DATA=JSON.parse(document.getElementById('grailData').textContent);const KEY='grail.personal.v071';const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
function key(r){return `${r.source_url}#${r.mint}`}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function load(){try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch{return {}}}
function save(s){localStorage.setItem(KEY,JSON.stringify(s))}
function toast(t){const x=$('#toast');x.textContent=t;x.classList.add('show');clearTimeout(toast.t);toast.t=setTimeout(()=>x.classList.remove('show'),1600)}
function parseFriends(){return $('#friends').value.split('\n').map(x=>x.trim()).filter(Boolean)}
function prefs(){const s=load();return{budget:Number($('#budget').value)||null,terms:$('#terms').value.split(',').map(x=>x.trim().toLowerCase()).filter(Boolean),cats:new Set($$('input[name=cat]:checked').map(x=>x.value)),mints:new Set($$('input[name=mint]:checked').map(x=>x.value)),owned:new Set(s.owned||[]),watch:new Set(s.watch||[]),friends:parseFriends()}}
function reasonText(r){return (r.reasons||[]).join(' ').toLowerCase()}
function friendMatch(r,lines){const owner=String(r.current_owner||r.onchain_owner||r.owner||'').toLowerCase();if(!owner)return null;for(const line of lines){const [name,h0]=line.split('|').map(x=>x&&x.trim());if(!name||!h0)continue;const h=h0.toLowerCase().replace('…','...');if(h.includes('...')){const [a,b]=h.split('...');if((!a||owner.startsWith(a))&&(!b||owner.endsWith(b)))return name}else if(owner===h)return name}return null}
function score(r,p){if(r.live_status!=='live'||!['GRAIL','EDGE','WATCH'].includes(r.signal_class)||r.actionability==='reject-price')return null;const k=key(r);if(p.owned.has(k))return null;const ask=Number(r.ask_usd||0);if(p.budget&&ask>p.budget)return null;let s=Number(r.opportunity_score||0)+(r.signal_class==='GRAIL'?16:r.signal_class==='EDGE'?6:0),why=[];if(p.watch.has(k)){s+=12;why.push('on your watchlist')}if(p.cats.has(r.category)){s+=10;why.push(`matches your ${r.category} universe`)}for(const t of p.terms){if(String(r.collectible||'').toLowerCase().includes(t)){s+=10;why.push(`matches your “${t}” interest`)}}const txt=reasonText(r),map={low:['low edition','top ~1%'],historical:['first','debut','release year','first-appearance'],ip:['earth-','order 66','501','identity'],patterns:['repeating','sequence','palindrom'],lucky8:['lucky-8','lucky 8','repeating 8']};for(const m of p.mints){if((map[m]||[]).some(t=>txt.includes(t))){s+=['low','historical','ip'].includes(m)?8:3;why.push(`matches your ${m} mint preference`)}}if(p.budget){s+=4;why.push('inside your budget')}const gap=Number(r.premium_to_floor_pct||0);if(gap<0)s+=Math.min(10,Math.abs(gap)/8);const fr=friendMatch(r,p.friends);if(fr){s-=8;why.push(`friend-owned / associated: ${fr}`)}return{...r,personal_score:s,personal_why:why}}
function pick(){const p=prefs(),rs=DATA.map(r=>score(r,p)).filter(Boolean).sort((a,b)=>b.personal_score-a.personal_score),out=[],seen=new Set(),cats={};for(const r of rs){if(seen.has(r.source_url)||(cats[r.category]||0)>=2)continue;out.push(r);seen.add(r.source_url);cats[r.category]=(cats[r.category]||0)+1;if(out.length===3)break}return out}
function card(r,i){const s=load(),k=key(r),watched=(s.watch||[]).includes(k),why=(r.personal_why&&r.personal_why.length?r.personal_why.join(' · '):(r.reasons||[r.why||'Market signal'])[0]),img=r.image_url?`<img src="${esc(r.image_url)}" alt="" loading="lazy">`:'';return `<article class="card" data-key="${esc(k)}"><div class="rank">0${i+1}</div><div class="media">${img}<span>${esc(r.signal_class)}</span></div><div class="body"><div class="meta"><span>${esc(r.category||'')}</span><b>${Math.round(r.confidence||0)}% evidence</b></div><h3>${esc(r.collectible)}</h3><div class="mint">Edition #${r.mint} <small>Mint ${Math.round(r.mint_score||0)}/100</small></div><div class="prices"><div><small>ASK</small><b>$${Number(r.ask_usd||0).toLocaleString(undefined,{maximumFractionDigits:2})}</b></div><div><small>FLOOR*</small><b>$${Number(r.floor_usd||0).toLocaleString(undefined,{maximumFractionDigits:2})}</b></div><div><small>POSITION</small><b>${Number(r.premium_to_floor_pct||0).toFixed(1)}%</b></div></div><p class="personalWhy">${esc(why)}</p><div class="badges"><span>● LIVE</span><span>${esc(r.signal_class)}</span>${watched?'<span>WATCHING</span>':''}</div><div class="actions">${r.stackr_url?`<a class="primary" href="${esc(r.stackr_url)}" target="_blank" rel="noopener">Open StackR ↗</a>`:''}${r.veve_url?`<a href="${esc(r.veve_url)}" target="_blank" rel="noopener">VeVe ↗</a>`:''}<a href="${esc(r.source_url)}" target="_blank" rel="noopener">Evidence ↗</a><button class="ownBtn" data-k="${esc(k)}">Mark owned</button><button class="watchBtn ${watched?'active':''}" data-k="${esc(k)}">${watched?'Watching ✓':'Watch'}</button></div></div></article>`}
function status(){const s=load();return `${(s.watch||[]).length} watched · ${(s.owned||[]).length} owned locally`}
function render(){const picks=pick(),g=$('#grid');g.innerHTML=picks.length?picks.map(card).join(''):'<div class="empty">Nothing clears your personal filters right now. That is useful information.</div>';$('#personalStatus').textContent=`${picks.length}/3 picks · ${status()}`;$$('.ownBtn').forEach(b=>b.onclick=()=>{const s=load(),o=new Set(s.owned||[]);o.add(b.dataset.k);s.owned=[...o];save(s);toast('Marked owned');render()});$$('.watchBtn').forEach(b=>b.onclick=()=>{const s=load(),w=new Set(s.watch||[]);w.has(b.dataset.k)?w.delete(b.dataset.k):w.add(b.dataset.k);s.watch=[...w];save(s);toast(w.has(b.dataset.k)?'Added to watchlist':'Removed from watchlist');render()})}
function hydrate(){const s=load();$('#budget').value=s.budget||'';$('#terms').value=(s.terms||[]).join(', ');$('#friends').value=(s.friends||[]).join('\n');$$('input[name=cat]').forEach(x=>x.checked=(s.cats||[]).includes(x.value));$$('input[name=mint]').forEach(x=>x.checked=(s.mints||[]).includes(x.value))}
function persistForm(){const p=prefs(),s=load();save({...s,version:71,budget:p.budget,terms:p.terms,cats:[...p.cats],mints:[...p.mints],friends:p.friends})}
$('#apply').onclick=()=>{persistForm();toast('Personal Hunter updated');render()};$('#reset').onclick=()=>{localStorage.removeItem(KEY);location.reload()};
$('#exportProfile').onclick=()=>{persistForm();const blob=new Blob([JSON.stringify(load(),null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='grail-personal-profile.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),500)};
$('#importProfile').onchange=async e=>{try{const f=e.target.files?.[0];if(!f)return;const obj=JSON.parse(await f.text());if(typeof obj!=='object'||Array.isArray(obj))throw new Error('bad profile');save(obj);hydrate();render();toast('Profile imported')}catch{toast('Invalid profile file')}};
$('#copyAlert').onclick=async()=>{persistForm();const s=load(),rules={version:1,budget_usd:s.budget||null,collectible_terms:s.terms||[],categories:s.cats||[],mint_preferences:s.mints||[],watch_keys:s.watch||[],exclude_owned:true};const text=JSON.stringify(rules,null,2);try{await navigator.clipboard.writeText(text);toast('Alert rules copied')}catch{prompt('Copy alert rules',text)}};
hydrate();render();'''

    document = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GRAIL Personal Hunter</title><style>{css}</style></head><body><main>
<section class="hero"><div class="eyebrow">GRAIL v0.7.1 · PERSONAL HUNTER</div><h1>Your market.<br>Your three moves.</h1><p>The global fallback is pre-rendered. Personal ranking happens privately in your browser from an embedded snapshot — no account, no API request after load, and no public profile.</p></section>
<section class="metrics"><div><small>TOP GLOBAL SIGNAL</small><b>{top}</b></div><div><small>GRAILS</small><b>{counts.get('GRAIL',0)}</b></div><div><small>EDGES</small><b>{counts.get('EDGE',0)}</b></div><div><small>LIVE CANDIDATES</small><b>{len(rows)}</b></div></section>
<section class="personal"><div class="personal-head"><div><div class="eyebrow">MY HUNTER</div><h2>Teach GRAIL what deserves your attention.</h2></div><div id="personalStatus" class="status">global fallback</div></div><div class="controls">
<div class="field"><label>Budget in USD</label><input id="budget" type="number" min="0" placeholder="e.g. 300"></div>
<div class="field"><label>Collectible / IP interests</label><input id="terms" type="text" placeholder="Spider-Man, Yoda, Mickey"></div>
<div class="field"><label>Universes</label><div class="cats">{category_options}</div></div>
<div class="field"><label>Mint preferences</label><div class="mints"><label><input type="checkbox" name="mint" value="low"> low mint</label><label><input type="checkbox" name="mint" value="historical"> historical</label><label><input type="checkbox" name="mint" value="ip"> IP-native</label><label><input type="checkbox" name="mint" value="lucky8"> lucky 8</label><label><input type="checkbox" name="mint" value="patterns"> patterns</label></div></div>
<div class="field"><label>Friends — local only</label><textarea id="friends" rows="3" placeholder="Friend | 0x12...abcd"></textarea></div></div>
<div class="buttons"><button id="apply">Apply Personal Hunter</button><button id="exportProfile" class="secondary">Export profile</button><label class="fileButton secondary">Import profile<input id="importProfile" type="file" accept="application/json" hidden></label><button id="copyAlert" class="secondary">Copy alert rules</button><button id="reset" class="secondary">Reset local profile</button></div>
<div class="privacy">Preferences, watchlist, owned items and friend aliases stay in this browser. Export happens only when you explicitly download a profile. Alert-rule export excludes friend aliases.</div></section>
<section id="grid" class="grid">{fallback}</section>
<script id="grailData" type="application/json">{embedded}</script><script>{js}</script><div id="toast" class="toast"></div></main></body></html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(document, encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "embedded_candidates": len(rows),
        "fallback_picks": len(picks),
        "categories": categories,
        "privacy_placeholder_generic": True,
        "watchlist": True,
        "profile_import_export": True,
        "alert_rules": True,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
