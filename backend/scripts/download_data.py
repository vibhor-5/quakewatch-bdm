"""Download monthly USGS ComCat earthquake CSVs (M2.5+) and write a provenance manifest."""
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import MIN_MAGNITUDE, RAW_DIR, YEARS  # noqa: E402

API = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def month_ranges():
    for y in YEARS:
        for m in range(1, 13):
            ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
            yield y, m, f"{y}-{m:02d}-01", f"{ny}-{nm:02d}-01"


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for y, m, start, end in month_ranges():
        params = dict(format="csv", starttime=start, endtime=end,
                      minmagnitude=MIN_MAGNITUDE, orderby="time-asc")
        r = requests.get(API, params=params, timeout=120)
        r.raise_for_status()
        path = RAW_DIR / f"usgs_{y}_{m:02d}.csv"
        path.write_bytes(r.content)
        manifest.append({
            "file": path.name, "url": r.url, "bytes": len(r.content),
            "sha256": hashlib.sha256(r.content).hexdigest(),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "rows": r.text.count("\n") - 1,
        })
        print(path.name, manifest[-1]["rows"])
        time.sleep(0.3)
    (RAW_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
