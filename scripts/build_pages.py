from __future__ import annotations

import html
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from api.opportunities import build_payload  # noqa: E402
from grail.inventory import annotate_payload, update_inventory_state  # noqa: E402
from grail.premium_model import build_premium_model  # noqa: E402
from grail.sales import scan_sales_watchlist  # noqa: E402


def _node(nodes: dict, node_id: str, kind: str, label: str, **attrs) -> None:
    nodes.setdefault(node_id, {"id": node_id, "kind": kind, "label": label, **attrs})


def _watch_meta() -> tuple[dict[str, dict], dict[str, dict]]:
    raw = json.loads((ROOT / "data" / "watchlist.json").read_text(encoding="utf-8"))
    return ({str(x["url"]): x for x in raw["collectibles"]}, {str(x["id"]): x for x in raw["collectibles"]})


def _sale_aware(payload: dict, sales: list) -> None:
    sale_index: dict[tuple[str, int], list] = defaultdict(list)
    for sale in sales:
        sale_index[(sale.source_url, sale.mint)].append(sale)
    for row in payload.get("candidates", []):
        matches = sale_index.get((row["source_url"], int(row["mint"])), [])
        listing_date = row.get("listed_date")
        later = [s for s in matches if s.sold_date and listing_date and s.sold_date >= listing_date]
        if not later:
            row["availability_status"] = "provider-current-unverified"
            continue
        latest = max(later, key=lambda s: s.sold_date or "")
        row["availability_status"] = "sold-after-listing"
        row["last_sale"] = {"date": latest.sold_date, "marketplace": latest.marketplace, "price_usd": latest.price_usd, "price_omi": latest.price_omi, "seller": latest.seller, "buyer": latest.buyer}
        if row.get("signal_class") in {"GRAIL", "EDGE", "WATCH"}:
            row["signal_class"] = "HISTORY"
            row["why"] = "A realised sale on/after the recorded listing date closes this opportunity. Kept as historical evidence."
    _resort(payload)


def _resort(payload: dict) -> None:
    order = {"GRAIL": 7, "EDGE": 6, "WATCH": 5, "MARKET": 4, "HISTORY": 3, "UNVERIFIED": 2, "REJECT": 1}
    payload["candidates"].sort(key=lambda r: (order.get(r.get("signal_class"), 0), r.get("opportunity_score", 0), r.get("mint_score", 0)), reverse=True)
    payload["counts"] = {key: sum(1 for r in payload["candidates"] if r.get("signal_class") == key) for key in order}


def _hunter_score(r: dict) -> float:
    score = float(r.get("opportunity_score") or 0)
    if r.get("signal_class") == "GRAIL": score += 15
    elif r.get("signal_class") == "EDGE": score += 5
    mint = float(r.get("mint_score") or 0)
    score += 6 if mint >= 75 else 3 if mint >= 45 else 0
    score += min(10, max(0, -float(r.get("premium_to_floor_pct") or 0)) / 8)
    score += max(0, (float(r.get("confidence") or 0) - 70) / 10)
    if r.get("owner_source_conflict"): score -= 10
    return score


def _choose_hunter(rows: list[dict]) -> list[dict]:
    eligible = [r for r in rows if r.get("live_status") == "live" and r.get("signal_class") in {"GRAIL", "EDGE", "WATCH"} and r.get("actionability") != "reject-price"]
    eligible.sort(key=_hunter_score, reverse=True)
    out, seen, cats = [], set(), defaultdict(int)
    for r in eligible:
        if r.get("source_url") in seen: continue
        cat = r.get("category") or "Other"
        if cats[cat] >= 2: continue
        out.append(r); seen.add(r.get("source_url")); cats[cat] += 1
        if len(out) == 3: break
    return out


def _semantic_reason(r: dict) -> str:
    reasons = r.get("reasons") or []
    strong = ("first", "debut", "earth-", "order 66", "501", "identity", "release year", "low edition", "top ~1%")
    weak = ("repeating", "lucky", "sequence", "palindrom")
    for reason in reasons:
        if any(x in reason.lower() for x in strong): return reason
    for reason in reasons:
        if any(x in reason.lower() for x in weak): return reason
    return "No thesis-grade mint reason yet — this is primarily a market-price edge."


def _render_static_hunter(payload: dict) -> tuple[str, list[dict]]:
    picks = _choose_hunter(payload.get("candidates", []))
    cards = []
    for i, r in enumerate(picks, 1):
        gap = float(r.get("premium_to_floor_pct") or 0)
        if r.get("signal_class") == "GRAIL" and gap <= 5:
            tag, why_now = "GRAIL", "thesis + sane economics"
        elif gap <= -15:
            tag, why_now = "PRICE EDGE", "large live dislocation"
        else:
            tag, why_now = "WATCH", "interesting, verify first"
        if r.get("owner_source_conflict"):
            risk = "Ownership sources disagree — exact-token evidence is preferred, but verify before acting."
        elif r.get("signal_class") == "EDGE" and float(r.get("mint_score") or 0) < 35:
            risk = "The mint itself is ordinary; the thesis is price dislocation, not collectibility."
        elif float(r.get("confidence") or 0) < 80:
            risk = "Evidence confidence is below 80%; verify the marketplace before acting."
        else:
            risk = "Floor is a snapshot and LIVE is provider-observed inventory, not a guaranteed executable quote."
        owner = "TOKEN ✓" if r.get("owner_evidence_level") == "exact-token" else "CHAIN ✓" if r.get("owner_status") == "verified-chain" else "OWNER ?"
        stackr = f'<a class="hunter-buy" href="{html.escape(str(r.get("stackr_url")))}" target="_blank" rel="noopener">Open StackR ↗</a>' if r.get("stackr_url") else ""
        veve = f'<a href="{html.escape(str(r.get("veve_url")))}" target="_blank" rel="noopener">VeVe ↗</a>' if r.get("veve_url") else ""
        image = f'<img src="{html.escape(str(r.get("image_url")))}" alt="">' if r.get("image_url") else ""
        cards.append(f'''<article class="hunter-card"><div class="hunter-rank">0{i}</div><div class="hunter-media">{image}<span>{html.escape(tag)}</span></div><div class="hunter-body"><div class="hunter-top"><span>{html.escape(str(r.get("category") or "Collectible"))}</span><b>{round(float(r.get("confidence") or 0))}% evidence</b></div><h3>{html.escape(str(r.get("collectible") or ""))}</h3><div class="hunter-mint">Edition #{r.get("mint")} <small>Mint {round(float(r.get("mint_score") or 0))}/100</small></div><div class="hunter-price"><div><small>ASK</small><b>${float(r.get("ask_usd") or 0):,.2f}</b></div><div><small>FLOOR*</small><b>${float(r.get("floor_usd") or 0):,.2f}</b></div><div><small>POSITION</small><b>{gap:+.1f}%</b></div></div><dl><div><dt>WHY NOW</dt><dd>{html.escape(why_now)} · observed LIVE in the current provider scan.</dd></div><div><dt>WHY THIS MINT</dt><dd>{html.escape(_semantic_reason(r))}</dd></div><div class="risk"><dt>RISK</dt><dd>{html.escape(risk)}</dd></div></dl><div class="hunter-proof"><span>● LIVE</span><span>{owner}</span><span>{html.escape(str(r.get("signal_class") or ""))}</span></div><div class="hunter-buttons">{stackr}{veve}<a href="{html.escape(str(r.get("source_url") or "#"))}" target="_blank" rel="noopener">Evidence ↗</a></div></div></article>''')
    if not cards:
        cards.append('<div class="hunter-empty">No live candidate clears Hunter today. That is useful information.</div>')
    section = f'''<section class="hunter" data-static="true"><div class="hunter-head"><div><p class="eyebrow">GRAIL HUNTER · TODAY</p><h2>Three things worth your attention.</h2><p>Pre-rendered from the latest market snapshot — no JavaScript required.</p></div><div class="hunter-meta"><b>{len(picks)}/3</b><span>qualified now</span></div></div><div class="hunter-grid">{''.join(cards)}</div><div class="hunter-actions"><a class="ghost-btn" href="./research.html">Open full research feed →</a><small>Hunter is selective by design.</small></div></section>'''
    return section, picks


def build_graph(payload: dict, sales: list, premium_stats: dict, inventory: dict) -> dict:
    nodes: dict[str, dict] = {}; edges: list[dict] = []; seen_edges: set[tuple[str, str, str]] = set()
    def edge(source: str, relation: str, target: str, evidence: str, observed_at: str | None = None) -> None:
        key = (source, relation, target)
        if key in seen_edges: return
        seen_edges.add(key); edges.append({"source": source, "relation": relation, "target": target, "evidence": evidence, "observed_at": observed_at})
    source_to_slug: dict[str, str] = {}
    for row in payload.get("candidates", []):
        slug = row["source_url"].rstrip("/").split("/")[-1]; source_to_slug[row["source_url"]] = slug
        collectible_id=f"collectible:{slug}"; mint_id=f"mint:{slug}:{row['mint']}"; market_id="marketplace:stackr"; category=row.get("category") or "Unknown"; category_id=f"universe:{category.lower().replace(' ', '-').replace('×', 'x')}"
        _node(nodes,category_id,"universe",category); _node(nodes,collectible_id,"collectible",row["collectible"],image_url=row.get("image_url"),veve_url=row.get("veve_url"),stackr_url=row.get("stackr_url")); _node(nodes,mint_id,"mint",f"#{row['mint']}",mint=row["mint"],mint_score=row.get("mint_score",0),signal_class=row.get("signal_class"),live_status=row.get("live_status"),availability_status=row.get("availability_status")); _node(nodes,market_id,"marketplace","StackR")
        edge(collectible_id,"belongs_to",category_id,row["source_url"],row.get("observed_at")); edge(collectible_id,"has_mint",mint_id,row["source_url"],row.get("observed_at")); edge(mint_id,"listed_on",market_id,row.get("stackr_url") or row["source_url"],row.get("observed_at"))
        price_id=f"price:{slug}:{row['mint']}:{row.get('ask_omi') or 0}"; _node(nodes,price_id,"price_observation",f"${row.get('ask_usd',0):.2f}",ask_usd=row.get("ask_usd"),ask_omi=row.get("ask_omi"),floor_usd=row.get("floor_usd"),premium_to_floor_pct=row.get("premium_to_floor_pct")); edge(mint_id,"priced_at",price_id,row["source_url"],row.get("observed_at"))
    for i,sale in enumerate(sales):
        slug=source_to_slug.get(sale.source_url,sale.source_url.rstrip("/").split("/")[-1]); collectible_id=f"collectible:{slug}"; mint_id=f"mint:{slug}:{sale.mint}"; sale_id=f"sale:{slug}:{sale.mint}:{sale.sold_date or i}:{sale.marketplace.lower()}"
        _node(nodes,collectible_id,"collectible",sale.collectible); _node(nodes,mint_id,"mint",f"#{sale.mint}",mint=sale.mint); _node(nodes,sale_id,"sale",f"{sale.marketplace} sale #{sale.mint}",price_usd=sale.price_usd,price_omi=sale.price_omi,sold_date=sale.sold_date); edge(collectible_id,"has_mint",mint_id,sale.source_url,sale.observed_at); edge(mint_id,"sold_in",sale_id,sale.source_url,sale.observed_at)
    for signal_kind,stat in premium_stats.items():
        node_id=f"premium:{signal_kind}"; attrs={k:v for k,v in stat.items() if k!="kind"}; _node(nodes,node_id,"realised_premium_evidence",signal_kind,**attrs)
    return {"generated_at":payload.get("generated_at"),"nodes":list(nodes.values()),"edges":edges,"stats":{"nodes":len(nodes),"edges":len(edges),"sales":len(sales),"premium_signal_types":len(premium_stats),"inventory":inventory.get("counts",{})},"premium_stats":premium_stats,"note":"Evidence graph. Historical buyers are not current owners. Provider-chain and exact-token owner evidence are tracked separately; exact-token conflicts are surfaced. Private friend/user overlays remain browser-local."}


def main() -> int:
    site=ROOT/"site"
    if site.exists(): shutil.rmtree(site)
    (site/"data").mkdir(parents=True)
    payload=build_payload(limit=250); sales,sale_errors=scan_sales_watchlist(ROOT/"data"/"watchlist.json",max_workers=10); _sale_aware(payload,sales)
    previous_inventory=None; inventory_path=ROOT/"data"/"inventory_state.json"
    if inventory_path.exists(): previous_inventory=json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory=update_inventory_state(previous_inventory,payload,sales); annotate_payload(payload,inventory); _resort(payload); (ROOT/"data"/"inventory_state.next.json").write_text(json.dumps(inventory,indent=2),encoding="utf-8")
    _,watch_by_id=_watch_meta(); premiums=build_premium_model(sales,watch_by_id,min_samples=10); graph=build_graph(payload,sales,premiums,inventory)
    (site/"data"/"opportunities.json").write_text(json.dumps(payload,indent=2),encoding="utf-8"); (site/"data"/"sales.json").write_text(json.dumps({"sales":[s.__dict__ for s in sales],"errors":sale_errors,"premium_stats":premiums},indent=2),encoding="utf-8"); (site/"data"/"inventory.json").write_text(json.dumps(inventory,indent=2),encoding="utf-8"); (site/"data"/"graph.json").write_text(json.dumps(graph,indent=2),encoding="utf-8")
    for name in ("index.html","research.html","styles.css","app.js","ownership-proof.js","hunter.js","hunter.css"):
        shutil.copy2(ROOT/"dashboard"/name,site/name)
    with (site/"styles.css").open("a",encoding="utf-8") as out: out.write("\n"); out.write((ROOT/"dashboard"/"pages-polish.css").read_text(encoding="utf-8"))

    # Pre-render Hunter and headline metrics so the public page is useful even with JS disabled or stale.
    hunter_html, picks = _render_static_hunter(payload)
    index_path = site/"index.html"; page = index_path.read_text(encoding="utf-8")
    page = page.replace('</section>\n    <section class="metrics">', '</section>\n    '+hunter_html+'\n    <section class="metrics">', 1)
    top_score = round(float(picks[0].get("opportunity_score") or 0)) if picks else 0
    page = page.replace('<span id="heroScore">—</span>', f'<span id="heroScore">{top_score}</span>', 1)
    page = page.replace('<strong id="grailCount">—</strong>', f'<strong id="grailCount">{payload.get("counts",{}).get("GRAIL",0)}</strong>', 1)
    page = page.replace('<strong id="edgeCount">—</strong>', f'<strong id="edgeCount">{payload.get("counts",{}).get("EDGE",0)}</strong>', 1)
    page = page.replace('<strong id="liveCount">—</strong>', f'<strong id="liveCount">{inventory.get("counts",{}).get("live",0)}</strong>', 1)
    page = page.replace('<strong id="omiPrice">—</strong>', f'<strong id="omiPrice">${float(payload.get("omi_usd") or 0):.8f}</strong>', 1)
    page = page.replace('<small id="scanTime">waiting for snapshot</small>', f'<small id="scanTime">snapshot {html.escape(str(payload.get("generated_at") or ""))}</small>', 1)
    index_path.write_text(page,encoding="utf-8")

    (site/".nojekyll").write_text("",encoding="utf-8"); shutil.copy2(site/"index.html",site/"404.html")
    errors=list(payload.get("errors",[]))+sale_errors; print(json.dumps({"candidates":len(payload.get("candidates",[])),"counts":payload.get("counts",{}),"sales":len(sales),"premium_signal_types":len(premiums),"inventory":inventory.get("counts",{}),"graph":graph["stats"],"hunter_static":len(picks),"research_page":True,"errors":errors},indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
