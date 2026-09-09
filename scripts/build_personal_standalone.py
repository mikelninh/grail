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
    reason = (r.get("reasons") or [r.get("why") or "Market signal"])[0]
    links: list[str] = []
    if r.get("stackr_url"):
        links.append(f'<a class="primary" href="{esc(r["stackr_url"])}" target="_blank" rel="noopener">Open StackR ↗</a>')
    if r.get("veve_url"):
        links.append(f'<a href="{esc(r["veve_url"])}" target="_blank" rel="noopener">VeVe ↗</a>')
    links.append(f'<a href="{esc(r.get("source_url"))}" target="_blank" rel="noopener">Evidence ↗</a>')
    return f'''<article class="card"><div class="rank">0{idx}</div><div class="media">{image}<span>{esc(r.get('signal_class'))}</span></div><div class="body"><div class="meta"><span>{esc(r.get('category'))}</span><b>{round(float(r.get('confidence') or 0))}% evidence</b></div><h3>{esc(r.get('collectible'))}</h3><div class="mint">Edition #{esc(r.get('mint'))} <small>Mint {round(float(r.get('mint_score') or 0))}/100</small></div><div class="prices"><div><small>ASK</small><b>${float(r.get('ask_usd') or 0):,.2f}</b></div><div><small>FLOOR*</small><b>${float(r.get('floor_usd') or 0):,.2f}</b></div><div><small>POSITION</small><b>{gap:+.1f}%</b></div></div><p class="personalWhy">{esc(reason)}</p><div class="badges"><span>● LIVE</span><span>{esc(r.get('signal_class'))}</span></div><div class="actions">{''.join(links)}</div></div></article>'''


def main() -> int:
    payload = json.loads((SITE / "data" / "opportunities.json").read_text(encoding="utf-8"))
    rows = eligible(payload.get("candidates", []))
    picks = choose(rows)
    counts = payload.get("counts", {})
    categories = sorted({str(r.get("category")) for r in rows if r.get("category")})
    embedded = json.dumps(rows, separators=(",", ":")).replace("</", "<\\/")
    fallback = "".join(fallback_card(r, i) for i, r in enumerate(picks, 1))
    top = round(global_score(picks[0])) if picks else "—"
    universe_options = '<option value="all">All universes</option>' + ''.join(
        f'<option value="{esc(c)}">{esc(c)}</option>' for c in categories
    )

    css = r'''*{box-sizing:border-box}body{margin:0;background:#090a0f;color:#f4f1e8;font-family:Inter,system-ui,sans-serif}main{max-width:1320px;margin:auto;padding:28px}h1,h2,h3{font-family:Georgia,serif;font-weight:400}.hero{padding:56px 0 28px;border-bottom:1px solid #282d39}.eyebrow{letter-spacing:.18em;color:#d9b867;font-size:10px;font-weight:800}.hero h1{font-size:clamp(46px,7vw,88px);line-height:.96;margin:12px 0}.hero p{max-width:820px;color:#9da5b3;line-height:1.6}.metrics{display:grid;grid-template-columns:repeat(4,1fr);margin:24px 0;border:1px solid #292e3a;border-radius:16px;overflow:hidden}.metrics div{padding:18px;border-right:1px solid #292e3a}.metrics div:last-child{border:0}.metrics small{display:block;color:#788092;font-size:9px}.metrics b{font-size:28px}.personal{border:1px solid #332f28;background:#111319;padding:22px;border-radius:18px;margin:24px 0}.personal-head{display:flex;justify-content:space-between;gap:20px;align-items:center}.personal h2{margin:3px 0 0}.preset-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:18px 0}.preset{border:1px solid #303644;background:#0d1016;color:#c5cad3;padding:11px 8px;border-radius:10px;font-weight:700;font-size:11px;cursor:pointer}.preset.active{border-color:#d9b867;background:#1a1811;color:#e4c676}.preset small{display:block;color:#757d8c;font-weight:500;margin-top:4px;line-height:1.25}.controls{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px}.field{display:flex;flex-direction:column;gap:6px}.field>label{font-size:9px;color:#8e96a6;text-transform:uppercase;letter-spacing:.1em}.field select,.field input[type=text],.field textarea{background:#0c0f15;color:#eee;border:1px solid #303644;border-radius:9px;padding:10px;width:100%}.toggles{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px}.toggles label{font-size:11px;color:#adb4c0}.custom{display:none;margin-top:14px;padding-top:14px;border-top:1px solid #272c37}.custom.show{display:grid;grid-template-columns:1fr 1fr;gap:12px}.buttons{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}.buttons button,.fileButton{border:1px solid #d9b867;background:#d9b867;color:#111;padding:10px 14px;border-radius:9px;font:700 12px Inter,system-ui;cursor:pointer}.buttons .secondary,.fileButton.secondary{background:transparent;color:#ccc;border-color:#303644}.privacy{font-size:10px;color:#697182;margin-top:10px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.card{position:relative;overflow:hidden;background:#11141b;border:1px solid #292e3a;border-radius:18px}.rank{position:absolute;z-index:2;top:12px;left:12px;font-size:10px;color:#e2c06e}.media{height:220px;position:relative;background:#171a22}.media img{width:100%;height:100%;object-fit:cover}.media span{position:absolute;bottom:10px;left:12px;background:#090b10cc;border:1px solid #554b32;color:#e2c06e;border-radius:99px;padding:5px 8px;font-size:9px}.body{padding:16px}.meta{display:flex;justify-content:space-between;color:#798192;font-size:9px;text-transform:uppercase}.body h3{font-size:22px;margin:9px 0}.mint{font-weight:800}.mint small{color:#d9b867}.prices{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin:13px 0}.prices div{background:#0b0e13;padding:9px;border-radius:8px}.prices small{display:block;color:#6f7787;font-size:8px}.personalWhy{min-height:55px;color:#a5acba;font-size:12px;line-height:1.5}.badges{display:flex;gap:5px;flex-wrap:wrap}.badges span{border:1px solid #303644;border-radius:99px;padding:4px 7px;font-size:8px}.actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:12px}.actions a,.actions button{padding:10px;border:1px solid #303644;border-radius:8px;text-align:center;color:#ddd;text-decoration:none;font:600 10px Inter,system-ui;background:transparent;cursor:pointer}.actions .primary{grid-column:1/-1;background:#eee7d5;color:#111;border-color:#eee7d5;font-weight:800}.actions .active{border-color:#d9b867;color:#e2c06e;background:#1a1811}.status{color:#d9b867;font-size:11px}.empty{grid-column:1/-1;padding:50px;border:1px dashed #303644;border-radius:14px;text-align:center;color:#8d95a4}.toast{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);background:#171a22;border:1px solid #353b49;padding:10px 14px;border-radius:9px;opacity:0;transition:.2s;pointer-events:none}.toast.show{opacity:1}@media(max-width:1000px){.preset-grid{grid-template-columns:repeat(2,1fr)}.controls{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}.metrics{grid-template-columns:1fr 1fr}}@media(max-width:620px){.controls,.custom{grid-template-columns:1fr}.preset-grid{grid-template-columns:1fr 1fr}.personal-head{align-items:flex-start;flex-direction:column}}'''

    js = r'''const DATA=JSON.parse(document.getElementById('grailData').textContent);const KEY='grail.personal.v072';const OLD='grail.personal.v071';const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const PRESETS={
'best':{name:'Best Overall',risk:'balanced',liquidity:'medium',price:'any',mint:'any'},
'grail':{name:'Grail Hunter',risk:'balanced',liquidity:'any',price:'sane',mint:'meaningful'},
'value':{name:'Value Hunter',risk:'balanced',liquidity:'medium',price:'below10',mint:'any'},
'low':{name:'Low Mint Hunter',risk:'balanced',liquidity:'any',price:'any',mint:'low'},
'iconic':{name:'Iconic Numbers',risk:'balanced',liquidity:'any',price:'any',mint:'meaningful'},
'sleeper':{name:'Sleeper',risk:'aggressive',liquidity:'medium',price:'below10',mint:'any'},
'liquid':{name:'Liquid',risk:'conservative',liquidity:'high',price:'sane',mint:'any'},
'moonshot':{name:'Moonshot',risk:'aggressive',liquidity:'any',price:'any',mint:'meaningful'},
'friend':{name:'Friend Radar',risk:'balanced',liquidity:'any',price:'any',mint:'any'},
'custom':{name:'Custom',risk:'balanced',liquidity:'any',price:'any',mint:'any'}};
function key(r){return `${r.source_url}#${r.mint}`}function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]))}
function load(){try{const now=JSON.parse(localStorage.getItem(KEY)||'{}');if(Object.keys(now).length)return now;return JSON.parse(localStorage.getItem(OLD)||'{}')}catch{return {}}}function save(s){localStorage.setItem(KEY,JSON.stringify(s))}
function toast(t){const x=$('#toast');x.textContent=t;x.classList.add('show');clearTimeout(toast.t);toast.t=setTimeout(()=>x.classList.remove('show'),1600)}
function ageDays(r){return Number(r.age_days??999)}function activity(r){const a=ageDays(r);return a<=2?'high':a<=7?'medium':'low'}function reasonText(r){return (r.reasons||[]).join(' ').toLowerCase()}
function mintKind(r){const t=reasonText(r);if(t.includes('low edition')||t.includes('top ~1%'))return 'low';if(/first|debut|release year|first-appearance|earth-|order 66|501|identity/.test(t))return 'meaningful';return 'ordinary'}
function parseFriends(){return $('#friends').value.split('\n').map(x=>x.trim()).filter(Boolean)}function friendMatch(r,lines){const owner=String(r.current_owner||r.onchain_owner||r.owner||'').toLowerCase();if(!owner)return null;for(const line of lines){const [name,h0]=line.split('|').map(x=>x&&x.trim());if(!name||!h0)continue;const h=h0.toLowerCase().replace('…','...');if(h.includes('...')){const [a,b]=h.split('...');if((!a||owner.startsWith(a))&&(!b||owner.endsWith(b)))return name}else if(owner===h)return name}return null}
function budgetCap(){const v=$('#budget').value;if(v==='any')return null;if(v==='custom')return Number($('#customBudget').value)||null;return Number(v)||null}
function current(){const s=load();return{preset:$('#preset').value,budget:budgetCap(),universe:$('#universe').value,mint:$('#mint').value,risk:$('#risk').value,liquidity:$('#liquidity').value,price:$('#price').value,hideMine:$('#hideMine').checked,hideFriends:$('#hideFriends').checked,watchFirst:$('#watchFirst').checked,terms:$('#terms').value.split(',').map(x=>x.trim().toLowerCase()).filter(Boolean),friends:parseFriends(),owned:new Set(s.owned||[]),watch:new Set(s.watch||[])}}
function passes(r,p){const k=key(r),ask=Number(r.ask_usd||0),gap=Number(r.premium_to_floor_pct||0),act=activity(r),mk=mintKind(r);if(p.hideMine&&p.owned.has(k))return false;if(p.budget&&ask>p.budget)return false;if(p.universe!=='all'&&r.category!==p.universe)return false;if(p.mint==='low'&&mk!=='low')return false;if(p.mint==='meaningful'&&mk==='ordinary')return false;if(p.liquidity==='high'&&act!=='high')return false;if(p.liquidity==='medium'&&act==='low')return false;if(p.price==='below10'&&gap>-10)return false;if(p.price==='below25'&&gap>-25)return false;if(p.price==='floor'&&gap>0)return false;if(p.price==='sane'&&gap>20)return false;const fr=friendMatch(r,p.friends);if(p.hideFriends&&fr)return false;return true}
function score(r,p){if(!passes(r,p))return null;const k=key(r),gap=Number(r.premium_to_floor_pct||0),mk=mintKind(r),act=activity(r),fr=friendMatch(r,p.friends);let s=Number(r.opportunity_score||0)+(r.signal_class==='GRAIL'?16:r.signal_class==='EDGE'?6:0),why=[];if(p.watchFirst&&p.watch.has(k)){s+=12;why.push('on your watchlist')}if(p.universe!=='all'){s+=8;why.push(`matches ${p.universe}`)}if(p.mint!=='any'&&mk!=='ordinary'){s+=8;why.push(mk==='low'?'low-mint fit':'meaningful-number fit')}if(gap<0){s+=Math.min(12,Math.abs(gap)/7);why.push(`${Math.abs(gap).toFixed(0)}% below floor snapshot`)}if(act==='high'){s+=6;why.push('fresh/high activity')}else if(act==='medium'){s+=2}if(p.risk==='conservative'){s+=(r.signal_class==='GRAIL'?8:0)+(act==='high'?5:0);if(Number(r.confidence||0)<80)s-=12}else if(p.risk==='aggressive'){s+=(gap<-25?8:0)+(mk!=='ordinary'?4:0)}if(p.preset==='grail')s+=(r.signal_class==='GRAIL'?14:0)+(mk!=='ordinary'?10:0);if(p.preset==='value')s+=gap<-20?12:gap<0?6:0;if(p.preset==='low')s+=mk==='low'?16:0;if(p.preset==='iconic')s+=mk==='meaningful'?16:0;if(p.preset==='sleeper')s+=(Number(r.ask_usd||0)<100?5:0)+(gap<-15?8:0);if(p.preset==='liquid')s+=act==='high'?14:0;if(p.preset==='moonshot')s+=(mk!=='ordinary'?10:0)+(Number(r.mint_score||0)>=70?8:0);if(p.preset==='friend'&&fr){s+=16;why.push(`friend radar: ${fr}`)}for(const t of p.terms){if(String(r.collectible||'').toLowerCase().includes(t)){s+=10;why.push(`matches “${t}”`)}}return{...r,personal_score:s,personal_why:why,friend:fr,activity:act,mint_kind:mk}}
function pick(){const p=current(),rs=DATA.map(r=>score(r,p)).filter(Boolean).sort((a,b)=>b.personal_score-a.personal_score),out=[],seen=new Set(),cats={};for(const r of rs){if(seen.has(r.source_url)||(cats[r.category]||0)>=2)continue;out.push(r);seen.add(r.source_url);cats[r.category]=(cats[r.category]||0)+1;if(out.length===3)break}return out}
function card(r,i){const s=load(),k=key(r),watched=(s.watch||[]).includes(k),why=(r.personal_why&&r.personal_why.length?r.personal_why.join(' · '):(r.reasons||[r.why||'Market signal'])[0]),img=r.image_url?`<img src="${esc(r.image_url)}" alt="" loading="lazy">`:'';return `<article class="card"><div class="rank">0${i+1}</div><div class="media">${img}<span>${esc(r.signal_class)}</span></div><div class="body"><div class="meta"><span>${esc(r.category||'')}</span><b>${Math.round(r.confidence||0)}% evidence</b></div><h3>${esc(r.collectible)}</h3><div class="mint">Edition #${r.mint} <small>Mint ${Math.round(r.mint_score||0)}/100</small></div><div class="prices"><div><small>ASK</small><b>$${Number(r.ask_usd||0).toLocaleString(undefined,{maximumFractionDigits:2})}</b></div><div><small>FLOOR*</small><b>$${Number(r.floor_usd||0).toLocaleString(undefined,{maximumFractionDigits:2})}</b></div><div><small>POSITION</small><b>${Number(r.premium_to_floor_pct||0).toFixed(1)}%</b></div></div><p class="personalWhy">${esc(why)}</p><div class="badges"><span>● LIVE</span><span>${esc(r.signal_class)}</span><span>${esc(r.activity||'')}</span>${watched?'<span>WATCHING</span>':''}</div><div class="actions">${r.stackr_url?`<a class="primary" href="${esc(r.stackr_url)}" target="_blank" rel="noopener">Open StackR ↗</a>`:''}${r.veve_url?`<a href="${esc(r.veve_url)}" target="_blank" rel="noopener">VeVe ↗</a>`:''}<a href="${esc(r.source_url)}" target="_blank" rel="noopener">Evidence ↗</a><button class="watchBtn ${watched?'active':''}" data-k="${esc(k)}">${watched?'Watching ✓':'Watch'}</button><button class="ownBtn" data-k="${esc(k)}">Mark owned</button></div></div></article>`}
function render(){const picks=pick(),g=$('#grid');g.innerHTML=picks.length?picks.map(card).join(''):'<div class="empty">Nothing clears these rules right now. That is useful information.</div>';$('#personalStatus').textContent=`${PRESETS[$('#preset').value].name} · ${picks.length}/3 picks`;$$('.watchBtn').forEach(b=>b.onclick=()=>{const s=load(),w=new Set(s.watch||[]);w.has(b.dataset.k)?w.delete(b.dataset.k):w.add(b.dataset.k);s.watch=[...w];save(s);render()});$$('.ownBtn').forEach(b=>b.onclick=()=>{const s=load(),o=new Set(s.owned||[]);o.add(b.dataset.k);s.owned=[...o];save(s);render();toast('Added to My GRAIL')})}
function applyPreset(id){const p=PRESETS[id];$('#preset').value=id;$('#risk').value=p.risk;$('#liquidity').value=p.liquidity;$('#price').value=p.price;$('#mint').value=p.mint;$$('.preset').forEach(b=>b.classList.toggle('active',b.dataset-preset===id));$('#custom').classList.toggle('show',id==='custom'||$('#budget').value==='custom');render()}
function persist(){const p=current(),s=load();save({...s,preset:p.preset,budgetChoice:$('#budget').value,customBudget:$('#customBudget').value,universe:p.universe,mint:p.mint,risk:p.risk,liquidity:p.liquidity,price:p.price,hideMine:p.hideMine,hideFriends:p.hideFriends,watchFirst:p.watchFirst,terms:p.terms,friends:p.friends});render()}
function hydrate(){const s=load(),preset=s.preset||'best';$('#budget').value=s.budgetChoice||'any';$('#customBudget').value=s.customBudget||'';$('#universe').value=s.universe||'all';$('#mint').value=s.mint||PRESETS[preset].mint;$('#risk').value=s.risk||PRESETS[preset].risk;$('#liquidity').value=s.liquidity||PRESETS[preset].liquidity;$('#price').value=s.price||PRESETS[preset].price;$('#hideMine').checked=s.hideMine!==false;$('#hideFriends').checked=!!s.hideFriends;$('#watchFirst').checked=s.watchFirst!==false;$('#terms').value=(s.terms||[]).join(', ');$('#friends').value=(s.friends||[]).join('\n');applyPreset(preset)}
$$('.preset').forEach(b=>b.onclick=()=>{applyPreset(b.dataset.preset);persist()});$('#budget').onchange=()=>{$('#custom').classList.toggle('show',$('#preset').value==='custom'||$('#budget').value==='custom');persist()};['universe','mint','risk','liquidity','price','hideMine','hideFriends','watchFirst'].forEach(id=>$('#'+id).onchange=persist);$('#apply').onclick=persist;$('#reset').onclick=()=>{localStorage.removeItem(KEY);location.reload()};
$('#exportProfile').onclick=()=>{const blob=new Blob([JSON.stringify({version:'0.7.2',profile:load()},null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='grail-hunter-profile.json';a.click();URL.revokeObjectURL(a.href)};$('#importProfile').onchange=async e=>{try{const x=JSON.parse(await e.target.files[0].text());save(x.profile||x);hydrate();render();toast('Profile imported')}catch{toast('Invalid profile')}};$('#copyAlert').onclick=async()=>{const p=current(),rules={version:'0.7.2',preset:p.preset,budget_usd:p.budget,universe:p.universe,mint:p.mint,risk:p.risk,liquidity:p.liquidity,price_position:p.price,hide_owned:p.hideMine,hide_friends:p.hideFriends,watch_first:p.watchFirst};try{await navigator.clipboard.writeText(JSON.stringify(rules,null,2));toast('Alert rules copied')}catch{toast('Could not copy')}};hydrate();render();'''
    js = js.replace("b.dataset-preset", "b.dataset.preset")

    preset_buttons = '''
<button class="preset" data-preset="best">Best Overall<small>balanced quality + price</small></button>
<button class="preset" data-preset="grail">Grail Hunter<small>thesis + meaningful mint</small></button>
<button class="preset" data-preset="value">Value Hunter<small>discount first</small></button>
<button class="preset" data-preset="low">Low Mint<small>low editions only</small></button>
<button class="preset" data-preset="iconic">Iconic Numbers<small>historical / IP numbers</small></button>
<button class="preset" data-preset="sleeper">Sleeper<small>cheap + overlooked</small></button>
<button class="preset" data-preset="liquid">Liquid<small>fresh activity first</small></button>
<button class="preset" data-preset="moonshot">Moonshot<small>scarcity + variance</small></button>
<button class="preset" data-preset="friend">Friend Radar<small>friend overlap first</small></button>
<button class="preset" data-preset="custom">Custom<small>advanced controls</small></button>'''

    document = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GRAIL Personal Hunter</title><style>{css}</style></head><body><main>
<section class="hero"><div class="eyebrow">GRAIL v0.7.2 · PERSONAL HUNTER</div><h1>Your market.<br>Your three moves.</h1><p>Choose a standard Hunter mode, then adjust only what matters. The global fallback is still pre-rendered and your private profile stays in this browser.</p></section>
<section class="metrics"><div><small>TOP GLOBAL SIGNAL</small><b>{top}</b></div><div><small>GRAILS</small><b>{counts.get('GRAIL',0)}</b></div><div><small>EDGES</small><b>{counts.get('EDGE',0)}</b></div><div><small>LIVE CANDIDATES</small><b>{len(rows)}</b></div></section>
<section class="personal"><div class="personal-head"><div><div class="eyebrow">MY HUNTER</div><h2>Choose your rules.</h2></div><div id="personalStatus" class="status">Best Overall</div></div>
<div class="preset-grid">{preset_buttons}</div><input id="preset" type="hidden" value="best">
<div class="controls">
<div class="field"><label>Budget</label><select id="budget"><option value="any">Any</option><option value="25">Under $25</option><option value="100">Under $100</option><option value="500">Under $500</option><option value="1000">Under $1k</option><option value="5000">Under $5k</option><option value="custom">Custom</option></select></div>
<div class="field"><label>Universe</label><select id="universe">{universe_options}</select></div>
<div class="field"><label>Mint importance</label><select id="mint"><option value="any">Any</option><option value="low">Low mint only</option><option value="meaningful">Meaningful numbers</option></select></div>
<div class="field"><label>Risk</label><select id="risk"><option value="conservative">Conservative</option><option value="balanced">Balanced</option><option value="aggressive">Aggressive</option></select></div>
<div class="field"><label>Liquidity</label><select id="liquidity"><option value="any">Any</option><option value="medium">Medium+</option><option value="high">High only</option></select></div>
<div class="field"><label>Price position</label><select id="price"><option value="any">Any</option><option value="sane">Sane economics</option><option value="floor">At / below floor</option><option value="below10">≥10% below</option><option value="below25">≥25% below</option></select></div>
</div>
<div class="toggles"><label><input id="hideMine" type="checkbox" checked> Hide mine</label><label><input id="hideFriends" type="checkbox"> Hide friends’</label><label><input id="watchFirst" type="checkbox" checked> Show watched first</label></div>
<div id="custom" class="custom"><div class="field"><label>Custom budget</label><input id="customBudget" type="text" inputmode="decimal" placeholder="e.g. 750"></div><div class="field"><label>Optional interests</label><input id="terms" type="text" placeholder="Spider-Man, Yoda, Mickey"></div><div class="field"><label>Friends — local only</label><textarea id="friends" rows="3" placeholder="Friend | 0x12...abcd"></textarea></div></div>
<div class="buttons"><button id="apply">Apply rules</button><button id="exportProfile" class="secondary">Export profile</button><label class="fileButton secondary">Import profile<input id="importProfile" type="file" accept="application/json" hidden></label><button id="copyAlert" class="secondary">Copy alert rules</button><button id="reset" class="secondary">Reset</button></div><div class="privacy">Standard presets are only scoring rules. Owned, watched and friend data remain local to this browser.</div></section>
<section id="grid" class="grid">{fallback}</section><script id="grailData" type="application/json">{embedded}</script><div id="toast" class="toast"></div><script>{js}</script></main></body></html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(document, encoding="utf-8")
    print(json.dumps({"output": str(OUT), "embedded_candidates": len(rows), "fallback_picks": len(picks), "presets": list(PRESETS.keys()) if False else 10, "standard_rules": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
