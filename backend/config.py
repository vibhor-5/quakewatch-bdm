"""Shared configuration for the QuakeWatch backend and scripts."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
EXPORT_DIR = ROOT / "data" / "exports"

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
DB_NAME = os.environ.get("QUAKEWATCH_DB", "quakewatch")

YEARS = (2024, 2025)
MIN_MAGNITUDE = 2.5
STRONG_MAGNITUDE = 5.0  # an event with mag >= 5.0 is "strong"

# Quake depth classes (km), following the usual shallow/intermediate/deep split.
DEPTH_BINS = [(None, 70.0, "Shallow"), (70.0, 300.0, "Intermediate"), (300.0, None, "Deep")]
MAG_CLASSES = [(2.5, 4.0, "Minor"), (4.0, 5.0, "Light"), (5.0, 6.0, "Moderate"),
               (6.0, 7.0, "Strong"), (7.0, None, "Major")]
GRID_DEGREES = 2.0

US_STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
}
