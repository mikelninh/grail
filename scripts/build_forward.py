from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grail.forward import update_forward_state  # noqa: E402


def main() -> int:
    opportunities_path = ROOT / "site" / "data" / "opportunities.json"
    sales_path = ROOT / "site" / "data" / "sales.json"
    state_path = ROOT / "data" / "forward_state.json"
    next_path = ROOT / "data" / "forward_state.next.json"
    public_path = ROOT / "site" / "data" / "forward.json"

    payload = json.loads(opportunities_path.read_text(encoding="utf-8"))
    sales_payload = json.loads(sales_path.read_text(encoding="utf-8"))
    previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else None
    state = update_forward_state(previous, payload, sales_payload.get("sales", []), now=payload.get("generated_at"))

    next_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    public_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(state.get("summary", {}), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
