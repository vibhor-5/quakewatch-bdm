"""Prepare the USGS data and load it into MongoDB with indexes."""
import json
import sys
from pathlib import Path

from pymongo import ASCENDING, GEOSPHERE, MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DB_NAME, EXPORT_DIR, MONGO_URI  # noqa: E402
from prepare import load_raw, prepare, summaries  # noqa: E402

KEEP = ["year", "month", "hour", "weekday", "date", "latitude", "longitude", "grid_id", "grid_lat",
        "grid_lon", "depth_km", "depth_class", "mag", "mag_class", "mag_type", "is_strong", "place",
        "region", "net", "status", "nst", "gap", "rms", "horizontalError", "depthError", "magError",
        "magNst", "log10_energy_j", "time", "updated"]


def to_docs(df):
    docs = []
    for rec in df[["id"] + KEEP].to_dict("records"):
        doc = {}
        for k, v in rec.items():
            if v is None or (isinstance(v, float) and v != v):
                continue
            if hasattr(v, "to_pydatetime"):
                v = v.to_pydatetime()
            elif hasattr(v, "item"):
                v = v.item()
            doc[k] = v
        doc["_id"] = doc.pop("id")
        doc["location"] = {"type": "Point", "coordinates": [doc["longitude"], doc["latitude"]]}
        docs.append(doc)
    return docs


def main():
    df, report = prepare(load_raw())
    daily, region = summaries(df)
    db = MongoClient(MONGO_URI)[DB_NAME]
    for name in ("earthquakes", "daily_summary", "region_summary"):
        db[name].drop()
    db.earthquakes.insert_many(to_docs(df), ordered=False)
    db.daily_summary.insert_many(daily.to_dict("records"))
    db.region_summary.insert_many(region.to_dict("records"))

    eq = db.earthquakes
    eq.create_index([("year", ASCENDING), ("is_strong", ASCENDING)], name="year_strong")
    eq.create_index([("date", ASCENDING), ("is_strong", ASCENDING)], name="date_strong")
    eq.create_index([("grid_id", ASCENDING), ("year", ASCENDING)], name="grid_year")
    eq.create_index([("mag", ASCENDING)], name="mag")
    eq.create_index([("region", ASCENDING), ("year", ASCENDING)], name="region_year")
    eq.create_index([("location", GEOSPHERE)], name="location_2dsphere")
    db.daily_summary.create_index([("date", ASCENDING)], unique=True, name="date_unique", partialFilterExpression={})
    db.region_summary.create_index([("region", ASCENDING), ("year", ASCENDING)], unique=True, name="region_year_unique")

    report["collections"] = {n: db[n].count_documents({}) for n in ("earthquakes", "daily_summary", "region_summary")}
    report["total_documents"] = sum(report["collections"].values())
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    (EXPORT_DIR / "import_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
