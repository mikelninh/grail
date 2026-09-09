from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from grail.provider_edition import lookup_edition  # noqa:E402

PAGE="https://vevealpha.com/c/marvel-disney-what-if-goofy-became-spider-man-common"


def main()->int:
    try:
        result=lookup_edition(PAGE,851,timeout=20)
        out=asdict(result)
        # The public browser config is intentionally never printed or persisted.
        print(json.dumps(out,indent=2))
    except Exception as exc:
        print(json.dumps({"edition":851,"status":"unresolved","error":f"{type(exc).__name__}: {exc}"},indent=2))
        return 2
    return 0

if __name__=="__main__": raise SystemExit(main())
