"""API tests. Run against a live MongoDB loaded with scripts/import_data.py (skipped if unavailable)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app  # noqa: E402
from prepare import region_of  # noqa: E402


@pytest.fixture(scope="module")
def client():
    app = create_app()
    try:
        app.config["DB"].earthquakes.estimated_document_count()
        if app.config["DB"].earthquakes.estimated_document_count() == 0:
            pytest.skip("database empty")
    except Exception:
        pytest.skip("MongoDB unavailable")
    return app.test_client()


def test_region_parsing():
    assert region_of("12 km N of Ridgecrest, California") == "United States"
    assert region_of("82 km N of Isangel, Vanuatu") == "Vanuatu"
    assert region_of("Banda Sea") == "Banda Sea"
    assert region_of(None) == "Unknown"


def test_health(client):
    j = client.get("/api/health").get_json()
    assert j["status"] == "ok" and j["collections"]["earthquakes"] > 0


def test_overview_totals_match_by_year(client):
    j = client.get("/api/overview").get_json()
    assert j["totals"]["events"] == sum(y["events"] for y in j["by_year"])
    assert j["totals"]["strong"] == sum(y["strong"] for y in j["by_year"])


def test_year_filter(client):
    a = client.get("/api/overview?year=2024").get_json()["totals"]["events"]
    b = client.get("/api/overview?year=2025").get_json()["totals"]["events"]
    assert a + b == client.get("/api/overview").get_json()["totals"]["events"]


def test_compare_baseline_ratio_is_not_degenerate(client):
    j = client.get("/api/compare?depth_class=Deep").get_json()
    assert j["baseline"]["strong"] > 0
    assert j["share_ratio"] and j["share_ratio"] != 1.0


def test_compare_no_filters_equals_baseline(client):
    j = client.get("/api/compare").get_json()
    assert j["scenario"] == j["baseline"] and j["share_ratio"] == 1.0


def test_temporal_sums(client):
    j = client.get("/api/temporal").get_json()
    total = client.get("/api/overview").get_json()["totals"]["events"]
    assert sum(h["events"] for h in j["hours"]) == total
    assert sum(w["events"] for w in j["weekdays"]) == total


def test_combinations_ratio_consistent(client):
    j = client.get("/api/combinations?min_count=100").get_json()
    base = j["baseline"]["share"]
    for g in j["groups"]:
        assert g["share_ratio"] == pytest.approx(g["share"] / base, abs=0.01)


def test_events_pagination_and_detail(client):
    j = client.get("/api/events?page=1").get_json()
    assert len(j["events"]) == 25 and j["pages"] > 1
    d = client.get(f"/api/events/{j['events'][0]['id']}").get_json()
    assert d["event"]["id"] == j["events"][0]["id"]
    assert client.get("/api/events/does-not-exist").status_code == 404
