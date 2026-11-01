"""QuakeWatch Flask API: MongoDB aggregation pipelines over USGS earthquake records."""
import math
import re
from datetime import timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient

from config import DB_NAME, MONGO_URI, YEARS

DEPTH_CLASSES = ("Shallow", "Intermediate", "Deep")
MAG_CLASSES = ("Minor", "Light", "Moderate", "Strong", "Major")
CONDITION_FIELDS = {"depth_class": "depth_class", "mag_type": "mag_type", "mag_class": "mag_class",
                    "status": "status", "network": "net"}


def create_app(db=None):
    app = Flask(__name__)
    CORS(app)
    app.config["DB"] = db if db is not None else MongoClient(MONGO_URI)[DB_NAME]

    def eq():
        return app.config["DB"].earthquakes

    # ---------- helpers ----------
    def year_filter():
        y = request.args.get("year", "all")
        try:
            y = int(y)
        except ValueError:
            return {}
        return {"year": y} if y in YEARS else {}

    def int_arg(name, default, lo, hi):
        try:
            return max(lo, min(hi, int(request.args.get(name, default))))
        except (TypeError, ValueError):
            return default

    def group_stats(match, key_expr, extra=None, sort=None, limit=None, min_count=1):
        """Group by key_expr and return events, strong and share (strong / events, in %)."""
        stage = {"_id": key_expr, "events": {"$sum": 1},
                 "strong": {"$sum": {"$cond": ["$is_strong", 1, 0]}}}
        stage.update(extra or {})
        pipe = [{"$match": match}, {"$group": stage}, {"$match": {"events": {"$gte": min_count}}},
                {"$sort": sort or {"_id": 1}}]
        if limit:
            pipe.append({"$limit": limit})
        rows = list(eq().aggregate(pipe))
        for r in rows:
            r["key"] = r.pop("_id")
            r["share"] = round(100 * r["strong"] / r["events"], 2) if r["events"] else None
        return rows

    def totals(match):
        r = list(eq().aggregate([{"$match": match}, {"$group": {
            "_id": None, "events": {"$sum": 1}, "strong": {"$sum": {"$cond": ["$is_strong", 1, 0]}},
            "max_mag": {"$max": "$mag"}, "mean_depth": {"$avg": "$depth_km"},
            "mean_mag": {"$avg": "$mag"}}}]))
        if not r:
            return {"events": 0, "strong": 0, "share": None, "max_mag": None,
                    "mean_depth": None, "mean_mag": None}
        r = r[0]
        return {"events": r["events"], "strong": r["strong"],
                "share": round(100 * r["strong"] / r["events"], 2), "max_mag": r["max_mag"],
                "mean_depth": round(r["mean_depth"], 1), "mean_mag": round(r["mean_mag"], 2)}

    def ratios(sub, base):
        """Share ratio and odds ratio of a subset against a baseline (dicts with events/strong)."""
        if not sub["events"] or not base["events"]:
            return {"share_ratio": None, "odds_ratio": None}
        p, pb = sub["strong"] / sub["events"], base["strong"] / base["events"]
        sr = p / pb if pb else None
        odds = (p / (1 - p)) / (pb / (1 - pb)) if 0 < p < 1 and 0 < pb < 1 else None
        return {"share_ratio": None if sr is None else round(sr, 2),
                "odds_ratio": None if odds is None else round(odds, 2)}

    def scenario_match():
        m = dict(year_filter())
        for arg, field in (("depth_class", "depth_class"), ("mag_type", "mag_type"),
                           ("region", "region"), ("status", "status"), ("network", "net")):
            v = request.args.get(arg)
            if v and v != "any":
                m[field] = v
        return m

    # ---------- endpoints ----------
    @app.get("/api/health")
    def health():
        db_ = app.config["DB"]
        return jsonify(status="ok", collections={n: db_[n].estimated_document_count()
                                                 for n in ("earthquakes", "daily_summary", "region_summary")})

    @app.get("/api/overview")
    def overview():
        match = year_filter()
        monthly = list(eq().aggregate([
            {"$match": match},
            {"$group": {"_id": {"year": "$year", "month": "$month"}, "events": {"$sum": 1},
                        "strong": {"$sum": {"$cond": ["$is_strong", 1, 0]}}, "max_mag": {"$max": "$mag"}}},
            {"$sort": {"_id.year": 1, "_id.month": 1}}]))
        monthly = [{"year": r["_id"]["year"], "month": r["_id"]["month"], "events": r["events"],
                    "strong": r["strong"], "max_mag": r["max_mag"]} for r in monthly]
        by_year = [{"year": r["key"], "events": r["events"], "strong": r["strong"], "share": r["share"]}
                   for r in group_stats({}, "$year")]
        return jsonify(totals=totals(match), monthly=monthly, by_year=by_year,
                       mag_classes=group_stats(match, "$mag_class", sort={"events": -1}))

    @app.get("/api/temporal")
    def temporal():
        match = year_filter()
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        weekdays = group_stats(match, "$weekday")
        for r in weekdays:
            r["label"] = names[r["key"]]
        return jsonify(hours=group_stats(match, "$hour"), weekdays=weekdays)

    @app.get("/api/conditions")
    def conditions():
        match = year_filter()
        out = {name: group_stats(match, f"${field}", sort={"events": -1}, limit=15)
               for name, field in CONDITION_FIELDS.items()}
        out["baseline"] = totals(match)
        return jsonify(out)

    @app.get("/api/hotspots")
    def hotspots():
        match = year_filter()
        min_count = int_arg("min_count", 25, 1, 100000)
        limit = int_arg("limit", 400, 1, 2000)
        rows = group_stats(match, "$grid_id",
                           extra={"lat": {"$first": "$grid_lat"}, "lon": {"$first": "$grid_lon"},
                                  "max_mag": {"$max": "$mag"}, "mean_depth": {"$avg": "$depth_km"}},
                           sort={"events": -1}, limit=limit, min_count=min_count)
        for r in rows:
            r["mean_depth"] = round(r["mean_depth"], 1)
        return jsonify(cells=rows, distinct_cells=len(eq().distinct("grid_id", match)),
                       limit=limit, min_count=min_count)

    @app.get("/api/regions")
    def regions():
        match = year_filter()
        rows = group_stats(match, "$region",
                           extra={"max_mag": {"$max": "$mag"}, "mean_depth": {"$avg": "$depth_km"}},
                           sort={"events": -1}, limit=int_arg("limit", 15, 1, 100),
                           min_count=int_arg("min_count", 1, 1, 100000))
        for r in rows:
            r["mean_depth"] = round(r["mean_depth"], 1)
        return jsonify(regions=rows)

    @app.get("/api/compare")
    def compare():
        """Compare a scenario (filters in the query string) with the selected year's baseline."""
        base = totals(year_filter())
        sub = totals(scenario_match())
        return jsonify(baseline=base, scenario=sub, **ratios(sub, base),
                       filters=dict(request.args.items()))

    @app.get("/api/combinations")
    def combinations():
        """Depth class x magnitude type groups ranked by strong share, with ratios to the baseline."""
        match = year_filter()
        min_count = int_arg("min_count", 100, 1, 100000)
        base = totals(match)
        rows = group_stats(match, {"depth_class": "$depth_class", "mag_type": "$mag_type"},
                           min_count=min_count)
        for r in rows:
            r["depth_class"], r["mag_type"] = r["key"]["depth_class"], r["key"]["mag_type"]
            r["key"] = f"{r['depth_class']} / {r['mag_type']}"
            r.update(ratios(r, base))
        rows.sort(key=lambda r: r["share"], reverse=True)
        return jsonify(baseline=base, groups=rows, min_count=min_count)

    @app.get("/api/options")
    def options():
        e = eq()
        return jsonify(depth_classes=list(DEPTH_CLASSES), mag_types=sorted(e.distinct("mag_type")),
                       statuses=sorted(e.distinct("status")), networks=sorted(e.distinct("net")),
                       regions=[r["key"] for r in group_stats({}, "$region", sort={"events": -1}, limit=60)])

    @app.get("/api/events")
    def events():
        page = int_arg("page", 1, 1, 100000)
        size = 25
        match = year_filter()
        if request.args.get("strong") == "1":
            match["is_strong"] = True
        if request.args.get("mag_class") in MAG_CLASSES:
            match["mag_class"] = request.args["mag_class"]
        q = (request.args.get("q") or "").strip()
        if q:
            match["$or"] = [{"_id": q}, {"place": {"$regex": re.escape(q), "$options": "i"}}]
        total = eq().count_documents(match)
        rows = list(eq().find(match, {"place": 1, "mag": 1, "mag_type": 1, "depth_km": 1, "time": 1,
                                      "region": 1, "mag_class": 1, "depth_class": 1, "status": 1})
                    .sort([("time", -1)]).skip((page - 1) * size).limit(size))
        for r in rows:
            r["id"] = r.pop("_id")
            r["time"] = r["time"].isoformat() + "Z"
        return jsonify(total=total, page=page, pages=max(1, math.ceil(total / size)), events=rows)

    @app.get("/api/events/<event_id>")
    def event_detail(event_id):
        doc = eq().find_one({"_id": event_id})
        if not doc:
            return jsonify(error="not found"), 404
        t0 = doc["time"]
        # Events within one day and 150 km: candidate foreshocks / aftershocks.
        nearby = list(eq().find({
            "_id": {"$ne": event_id},
            "time": {"$gte": t0 - timedelta(days=1), "$lte": t0 + timedelta(days=1)},
            "location": {"$geoWithin": {"$centerSphere": [doc["location"]["coordinates"], 150 / 6378.1]}},
        }, {"mag": 1, "place": 1, "time": 1, "depth_km": 1}).sort("time", 1).limit(50))
        doc["id"] = doc.pop("_id")
        for d in [doc, *nearby]:
            d["id"] = d.pop("_id", d.get("id"))
            for k in ("time", "updated"):
                if k in d:
                    d[k] = d[k].isoformat() + "Z"
        return jsonify(event=doc, nearby=nearby)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
