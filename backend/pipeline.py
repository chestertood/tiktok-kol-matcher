import json
import re
from pathlib import Path

from backend.brand import analyze_brand
from backend.facebook_client import normalize_url
from backend.rank import add_pitches, rank
from backend.tiktok import find_creators

RESULTS = Path(__file__).resolve().parent.parent / "results.json"  # latest run
RUNS = RESULTS.parent / "runs"  # one file per Facebook page
SAMPLE = RESULTS.parent / "examples" / "sample_results.json"


def run(facebook, website=None, per_tier=5):
    """Facebook URL -> (brand analysis, {tier: ranked KOLs with outreach drafts}).
    Saved to results.json (latest) and runs/<page>.json (kept per page)."""
    brand = analyze_brand(facebook, website)
    print(f"brand: {brand['brand']} | queries: {brand['tiktok_queries']}")
    ranked = add_pitches(brand, rank(brand, find_creators(brand["tiktok_queries"]), per_tier=per_tier))
    payload = json.dumps({"facebook": facebook, "brand": brand, "ranked": ranked}, ensure_ascii=False)
    RUNS.mkdir(exist_ok=True)
    slug = re.sub(r"\W+", "_", normalize_url(facebook).split("facebook.com/")[1])
    (RUNS / f"{slug}.json").write_text(payload, encoding="utf-8")
    RESULTS.write_text(payload, encoding="utf-8")
    return brand, ranked


def saved_runs():
    """Result files that can be reopened without scraping: past runs (newest first), then the bundled sample."""
    runs = sorted(RUNS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return runs + ([SAMPLE] if SAMPLE.exists() else [])


def parse_results(text):
    """results .json text -> (brand, ranked); ValueError if it is not a results file."""
    d = json.loads(text)
    if not isinstance(d, dict) or not {"brand", "ranked"} <= d.keys():
        raise ValueError("not a KOL results file (expects keys: brand, ranked)")
    return d["brand"], d["ranked"]


if __name__ == "__main__":
    assert parse_results('{"brand": {"brand": "B"}, "ranked": {}}') == ({"brand": "B"}, {})
    for bad in ("[]", '{"x": 1}'):
        try:
            parse_results(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad}")
    print("ok")
