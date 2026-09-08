from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grail.mint_live import fetch_stackr_owner  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        stackr_url = query.get("url", [""])[0]
        try:
            mint = int(query.get("mint", [""])[0])
        except ValueError:
            mint = 0

        if not stackr_url or mint <= 0:
            payload = {"status": "error", "owner": None, "message": "url and positive mint are required"}
            status = 400
        else:
            try:
                owner = fetch_stackr_owner(stackr_url, mint)
                payload = {
                    "status": "resolved" if owner else "unresolved",
                    "owner": owner,
                    "message": "Owner parsed from StackR listing page" if owner else "Owner not exposed in server-rendered StackR markup; verify on StackR before buying",
                }
                status = 200
            except Exception as exc:
                payload = {"status": "error", "owner": None, "message": f"{type(exc).__name__}: {exc}"}
                status = 400

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "s-maxage=60")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
