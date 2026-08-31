"""
Load a company profile and run it against the SEC.

A profile is the per-company judgment layer (ingest/profiles/*.yaml); the
engine in ingest/edgar/ is generic. This module joins the two: given a ticker,
it finds the profile (or falls back to the generic one), pulls each KPI, and
returns a result that carries its own confidence tier.

The tier is not cosmetic. Generic output is produced by guessing that the
obvious concept is the right one, which for Redwood would have given a
leverage figure roughly 6x too high, an expense series that silently stopped
in 2024, and four quarters of negative operating expenses. Anything shown to
a user must display which tier it came from.
"""

import os

import yaml

from ingest.edgar import client, facts

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")


def load(ticker):
    """Return (profile dict, is_curated).

    Falls back to _default.yaml for any company nobody has curated, filling in
    identity from the SEC ticker map.
    """
    path = os.path.join(PROFILE_DIR, f"{ticker.lower()}.yaml")
    if os.path.exists(path):
        with open(path) as handle:
            return yaml.safe_load(handle), True

    with open(os.path.join(PROFILE_DIR, "_default.yaml")) as handle:
        profile = yaml.safe_load(handle)

    cik, name = client.ticker_to_cik(ticker)
    profile.update({"ticker": ticker.upper(), "cik": cik, "name": name})
    return profile, False


def company_facts(cik):
    """CompanyFacts for one company, cached - it is a large document."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    path, _ = client.cached_get(url, f"companyfacts_{cik}.json")
    import json

    with open(path) as handle:
        return json.load(handle)


def run(ticker):
    """Extract every KPI the profile declares.

    A concept the filer never reported is recorded as unavailable rather than
    skipped silently - for a generic profile that absence is itself the useful
    signal, since it usually means the company tags something else instead.
    """
    profile, curated = load(ticker)
    data = company_facts(profile["cik"])
    us_gaap = data["facts"]["us-gaap"]

    results = {}
    for spec in profile.get("kpis", []):
        key = spec["key"]
        try:
            if spec["kind"] == "instant":
                by_frame = facts.latest_instant_by_frame(us_gaap, spec["concept"])
                series = {
                    frame[:-1]: record["val"] for frame, record in by_frame.items()
                }
            else:
                records, _ = facts.concept_records(
                    us_gaap, spec["concept"], spec.get("successors", ())
                )
                by_frame = facts.dedupe_by_frame(records)
                quarterly = facts.quarterly_from_frames(by_frame, "value")
                derived = facts.derive_q4(by_frame, quarterly, "value")
                merged = facts.merge_reported_and_derived(quarterly, derived, "value")
                series = {frame: row["value"] for frame, row in merged.items()}
        except KeyError as error:
            results[key] = {"label": spec["label"], "available": False, "reason": str(error)}
            continue

        quarters = sorted(series)
        results[key] = {
            "label": spec["label"],
            "available": True,
            "unit": spec.get("unit"),
            "quarters": len(quarters),
            "first": quarters[0] if quarters else None,
            "latest": quarters[-1] if quarters else None,
            "latest_value": series[quarters[-1]] if quarters else None,
            "note": spec.get("note"),
        }

    return {
        "ticker": profile["ticker"],
        "name": profile["name"],
        "cik": profile["cik"],
        "tier": "curated" if curated else "generic",
        "kpis": results,
        "caveats": profile.get("caveats", []),
    }
