"""Data preparation: raw USGS CSVs -> clean DataFrame with derived analytical fields."""
import glob
import re

import numpy as np
import pandas as pd

from config import (DEPTH_BINS, GRID_DEGREES, MAG_CLASSES, RAW_DIR, STRONG_MAGNITUDE, US_STATES)


def label_bins(values: pd.Series, bins) -> pd.Series:
    out = pd.Series(index=values.index, dtype="object")
    for lo, hi, name in bins:
        mask = pd.Series(True, index=values.index)
        if lo is not None:
            mask &= values >= lo
        if hi is not None:
            mask &= values < hi
        out[mask] = name
    return out


def region_of(place) -> str:
    """Region = text after the last comma of USGS `place`; US states collapse to the US."""
    if not isinstance(place, str) or not place.strip():
        return "Unknown"
    tail = place.split(",")[-1].strip()
    if tail in US_STATES or tail in ("CA", "NV", "AK", "HI"):
        return "United States"
    # Some places have no comma, e.g. "Banda Sea" or "east of the North Island of New Zealand".
    if "," not in place:
        m = re.search(r"of (?:the )?(.+)$", place)
        tail = (m.group(1) if m else place).strip()
    return tail


def load_raw() -> pd.DataFrame:
    files = sorted(glob.glob(str(RAW_DIR / "usgs_*.csv")))
    if not files:
        raise SystemExit("No raw CSVs found; run scripts/download_data.py first.")
    return pd.concat((pd.read_csv(f) for f in files), ignore_index=True)


def prepare(raw: pd.DataFrame):
    report = {"raw_rows": int(len(raw))}
    df = raw.drop_duplicates("id").copy()
    report["duplicates_removed"] = int(len(raw) - len(df))
    non_quake = df["type"] != "earthquake"
    report["non_earthquake_excluded"] = int(non_quake.sum())
    df = df[~non_quake].copy()

    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["updated"] = pd.to_datetime(df["updated"], utc=True)
    df["year"] = df["time"].dt.year
    df["month"] = df["time"].dt.month
    df["hour"] = df["time"].dt.hour
    df["weekday"] = df["time"].dt.weekday  # 0 = Monday
    df["date"] = df["time"].dt.strftime("%Y-%m-%d")

    valid_coord = df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)
    report["invalid_coordinates"] = int((~valid_coord).sum())
    df = df[valid_coord & df["mag"].notna() & df["depth"].notna()].copy()

    df["depth_km"] = df["depth"]
    df["depth_class"] = label_bins(df["depth_km"], DEPTH_BINS)
    df["mag_class"] = label_bins(df["mag"], MAG_CLASSES)
    df["is_strong"] = df["mag"] >= STRONG_MAGNITUDE
    df["region"] = df["place"].map(region_of)
    df["mag_type"] = df["magType"].fillna("unknown").str.lower()

    g = GRID_DEGREES
    lat_c = (np.floor(df["latitude"] / g) * g + g / 2).round(2)
    lon_c = (np.floor(df["longitude"] / g) * g + g / 2).round(2)
    df["grid_lat"], df["grid_lon"] = lat_c, lon_c
    df["grid_id"] = lat_c.astype(str) + "_" + lon_c.astype(str)
    # Radiated energy (J) from the Gutenberg-Richter relation log10 E = 1.5 M + 4.8
    df["log10_energy_j"] = 1.5 * df["mag"] + 4.8
    report["clean_rows"] = int(len(df))
    return df.reset_index(drop=True), report


def summaries(df: pd.DataFrame):
    daily = (df.groupby(["date", "year"]).agg(
        events=("mag", "size"), strong=("is_strong", "sum"), max_mag=("mag", "max"),
        mean_depth_km=("depth_km", "mean")).reset_index())
    daily["mean_depth_km"] = daily["mean_depth_km"].round(2)
    region = (df.groupby(["region", "year"]).agg(
        events=("mag", "size"), strong=("is_strong", "sum"), max_mag=("mag", "max"),
        mean_depth_km=("depth_km", "mean"), mean_lat=("latitude", "mean"),
        mean_lon=("longitude", "mean")).reset_index())
    region[["mean_depth_km", "mean_lat", "mean_lon"]] = region[["mean_depth_km", "mean_lat", "mean_lon"]].round(2)
    return daily, region
