"""Export the star-schema CSV tables used by the BI dashboard (Power BI or the bundled HTML one)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import EXPORT_DIR, YEARS  # noqa: E402
from prepare import load_raw, prepare  # noqa: E402


def stat_table(df, by, min_events=1):
    t = df.groupby(by).agg(events=("mag", "size"), strong=("is_strong", "sum"),
                           max_mag=("mag", "max"), mean_depth_km=("depth_km", "mean")).reset_index()
    t["strong_share_pct"] = (100 * t["strong"] / t["events"]).round(2)
    t["mean_depth_km"] = t["mean_depth_km"].round(1)
    return t[t["events"] >= min_events]


def main():
    df, _ = prepare(load_raw())
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    fact = df[["id", "date", "year", "month", "hour", "weekday", "latitude", "longitude", "grid_id", "depth_km",
               "depth_class", "mag", "mag_class", "mag_type", "is_strong", "region", "net", "status",
               "place", "log10_energy_j"]].rename(columns={"id": "event_id", "net": "network"})
    fact["is_strong"] = fact["is_strong"].astype(int)
    fact.to_csv(EXPORT_DIR / "fact_earthquakes.csv", index=False)

    dates = pd.date_range(f"{YEARS[0]}-01-01", f"{YEARS[-1]}-12-31")
    pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "year": dates.year, "month": dates.month,
                  "month_name": dates.strftime("%b"), "weekday": dates.day_of_week,
                  "weekday_name": dates.strftime("%a")}).to_csv(EXPORT_DIR / "dim_calendar.csv", index=False)

    hot = stat_table(df, ["grid_id", "grid_lat", "grid_lon", "year"], min_events=5)
    hot.to_csv(EXPORT_DIR / "agg_hotspots_grid.csv", index=False)

    parts = []
    for col in ("depth_class", "mag_type", "mag_class", "status", "net"):
        t = stat_table(df, [col, "year"]).rename(columns={col: "value"})
        t.insert(0, "condition_type", "network" if col == "net" else col)
        parts.append(t)
    pd.concat(parts).to_csv(EXPORT_DIR / "agg_conditions.csv", index=False)

    stat_table(df, ["region", "year"], min_events=5).to_csv(EXPORT_DIR / "agg_regions.csv", index=False)
    stat_table(df, ["depth_class", "mag_class", "year"]).to_csv(EXPORT_DIR / "agg_depth_mag_matrix.csv", index=False)
    for f in sorted(EXPORT_DIR.glob("*.csv")):
        print(f.name, sum(1 for _ in open(f)) - 1)


if __name__ == "__main__":
    main()
