"""Benchmark representative queries with explain('executionStats'): indexed vs forced $natural scan."""
import json
import statistics
import sys
from pathlib import Path

from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DB_NAME, EXPORT_DIR, MONGO_URI  # noqa: E402

RUNS = 5
TOKYO = [139.69, 35.69]
R_KM = 300


def stages(plan):
    out = []
    while plan:
        out.append(plan["stage"])
        plan = plan.get("inputStage") or (plan.get("inputStages") or [None])[0]
    return out


def explain(coll, flt, hint):
    cmd = {"find": coll.name, "filter": flt, "hint": hint}
    ex = coll.database.command({"explain": cmd, "verbosity": "executionStats"})
    es = ex["executionStats"]
    return es, ex["queryPlanner"]["winningPlan"]


def run(coll, name, flt, index_hint):
    rows = []
    for label, hint in (("index", index_hint), ("collection scan", {"$natural": 1})):
        times, last = [], None
        for _ in range(RUNS):
            es, plan = explain(coll, flt, hint)
            times.append(es["executionTimeMillis"])
            last = (es, plan)
        es, plan = last
        rows.append({"query": name, "access_path": label, "median_ms": statistics.median(times),
                     "all_ms": times, "keys_examined": es["totalKeysExamined"],
                     "docs_examined": es["totalDocsExamined"], "returned": es["nReturned"],
                     "stages": stages(plan)})
        print(rows[-1])
    return rows


def main():
    coll = MongoClient(MONGO_URI)[DB_NAME].earthquakes
    sample_id = coll.find_one({"year": 2025, "is_strong": True})["_id"]
    results = []
    results += run(coll, "2025 strong events", {"year": 2025, "is_strong": True}, "year_strong")
    results += run(coll, "event id lookup", {"_id": sample_id}, {"_id": 1})
    results += run(coll, f"within {R_KM} km of Tokyo",
                   {"location": {"$geoWithin": {"$centerSphere": [TOKYO, R_KM / 6378.1]}}}, "location_2dsphere")
    results += run(coll, "magnitude >= 6", {"mag": {"$gte": 6.0}}, "mag")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    (EXPORT_DIR / "benchmark.json").write_text(json.dumps(
        {"runs_per_path": RUNS, "server_version": coll.database.client.server_info()["version"],
         "docs_in_collection": coll.estimated_document_count(), "results": results}, indent=2))


if __name__ == "__main__":
    main()
