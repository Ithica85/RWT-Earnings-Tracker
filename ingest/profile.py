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

import csv
import os

import yaml

from ingest.edgar import client, facts

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")

# The standalone extraction scripts predate the ingest package and still write
# their CSVs to the repo root, which is where derived_elsewhere resolves paths.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _quarter_key(frame):
    """Chronological sort for CY2026Q2 labels.

    String sorting happens to work for same-length labels but breaks the
    moment anything else is mixed in, so the ordering is made explicit.
    """
    return (int(frame[2:6]), int(frame[-1]))


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


def _summarise(spec, series):
    """Shape one KPI for export, given a {quarter: value} mapping.

    Both extraction paths end here - concepts pulled from CompanyFacts and
    series read back from a script's CSV - so a derived measure is
    indistinguishable from a tagged one everywhere downstream.
    """
    quarters = sorted(series, key=_quarter_key)
    return {
        "label": spec["label"],
        "available": True,
        "unit": spec.get("unit"),
        "quarters": len(quarters),
        "first": quarters[0] if quarters else None,
        "latest": quarters[-1] if quarters else None,
        "latest_value": series[quarters[-1]] if quarters else None,
        "note": spec.get("note"),
        # Full series, for charting and for the web export. Ordered
        # chronologically rather than lexically so CY2009Q2 precedes
        # CY2010Q1 regardless of string comparison.
        "series": [{"quarter": q, "value": series[q]} for q in quarters],
    }


def _series_from_csv(spec):
    """Read a measure CompanyFacts cannot produce, from the CSV its script writes.

    Recourse leverage, book value per share and operating expenses each cost a
    separate investigation - MD&A prose that is tagged nowhere, a preferred
    stock subtraction, a four-component splice against custom tags. That work
    lives in the scripts the profile names, so the series is read back rather
    than reimplemented here where a second version could drift from the first.

    A missing file raises rather than marking the KPI unavailable. A profile
    asserting a measure exists while the app quietly ships without it is the
    exact failure this block was written to fix.
    """
    for field in ("csv", "column", "label"):
        if field not in spec:
            raise KeyError(
                f"{spec.get('key')}: derived_elsewhere entry needs a '{field}'"
            )

    path = os.path.join(REPO_ROOT, spec["csv"])
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{spec['key']}: {spec['csv']} is missing - "
            f"run {spec.get('script', 'its script')} to build it"
        )

    series = {}
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            value = (row.get(spec["column"]) or "").strip()
            if value:
                series[row["quarter"]] = float(value)

    if not series:
        raise ValueError(
            f"{spec['key']}: no values in {spec['csv']} column '{spec['column']}'"
        )
    return series


def run(ticker):
    """Extract every KPI the profile declares, from both of its sources.

    A concept the filer never reported is recorded as unavailable rather than
    skipped silently - for a generic profile that absence is itself the useful
    signal, since it usually means the company tags something else instead.

    Measures under `derived_elsewhere` come from the CSVs the standalone
    scripts write, because CompanyFacts cannot produce them for this company
    at all. They are merged into the same result, so nothing downstream needs
    to know which source a figure came from.
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

        results[key] = _summarise(spec, series)

    for spec in profile.get("derived_elsewhere", []):
        results[spec["key"]] = _summarise(spec, _series_from_csv(spec))

    return {
        "ticker": profile["ticker"],
        "name": profile["name"],
        "cik": profile["cik"],
        "tier": "curated" if curated else "generic",
        "kpis": results,
        "caveats": profile.get("caveats", []),
    }
