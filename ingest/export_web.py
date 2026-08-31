"""
Generate the JSON the web app builds from.

Deliberately not a database. The whole corpus is well under a megabyte and
changes four times a year, when companies file. A Postgres instance at this
size would add provisioning, connection handling and running cost while
buying nothing - so the pipeline emits static JSON and Next.js turns it into
static pages at build time.

That stops being true in Phase 3, when arbitrary tickers are generated on
demand rather than curated ahead of time. Everything the app reads goes
through web/lib/data.ts, so swapping the source is one module's problem.

    python3 -m ingest.export_web            # default company set
    python3 -m ingest.export_web RWT NLY    # explicit
"""

import json
import os
import sys

from ingest import profile
from ingest.signals import eight_k

COMPANIES = ["RWT", "NLY", "AGNC", "PMT", "MFA"]
SIGNALS_SINCE = "2024-01-01"

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "data"
)


def derived_ratios(kpis):
    """Ratios computable from KPIs already extracted, per quarter.

    Only gross debt-to-equity for now. It is deliberately emitted despite
    being the most misleading number in the set, because hiding it would not
    stop anyone computing it themselves - the app pairs it with its caveat
    instead.
    """
    liabilities = kpis.get("total_liabilities", {})
    equity = kpis.get("stockholders_equity", {})
    if not (liabilities.get("available") and equity.get("available")):
        return {}

    by_quarter = {p["quarter"]: p["value"] for p in equity["series"]}
    series = []
    for point in liabilities["series"]:
        eq = by_quarter.get(point["quarter"])
        if eq:
            series.append(
                {"quarter": point["quarter"], "value": round(point["value"] / eq, 2)}
            )

    if not series:
        return {}

    return {
        "debt_to_equity": {
            "label": "Debt-to-Equity (gross)",
            "available": True,
            "unit": "multiple",
            "quarters": len(series),
            "first": series[0]["quarter"],
            "latest": series[-1]["quarter"],
            "latest_value": series[-1]["value"],
            "series": series,
            "note": "Total liabilities over stockholders' equity. See caveats.",
        }
    }


def build(ticker, signals):
    """Assemble one company's payload."""
    data = profile.run(ticker)
    data["kpis"].update(derived_ratios(data["kpis"]))
    data["signals"] = signals.get(ticker, {}).get("signals", [])
    return data


def main():
    tickers = sys.argv[1:] or COMPANIES
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Collecting 8-K signals since {SIGNALS_SINCE}")
    signals = eight_k.collect_many(tickers, since=SIGNALS_SINCE)

    index = []
    for ticker in tickers:
        payload = build(ticker, signals)
        path = os.path.join(OUT_DIR, f"{ticker.lower()}.json")
        with open(path, "w") as handle:
            json.dump(payload, handle, indent=2)

        available = sum(1 for k in payload["kpis"].values() if k["available"])
        size = os.path.getsize(path) / 1024
        print(
            f"  {ticker:5} {payload['tier']:8} "
            f"{available:>2} KPIs  {len(payload['signals']):>2} signals  "
            f"{size:>6.0f} KB"
        )

        index.append(
            {
                "ticker": payload["ticker"],
                "name": payload["name"],
                "tier": payload["tier"],
                "latest_quarter": payload["kpis"].get("total_assets", {}).get("latest"),
                "kpi_count": available,
                "signal_count": len(payload["signals"]),
                "caveat_count": len(payload["caveats"]),
            }
        )

    with open(os.path.join(OUT_DIR, "index.json"), "w") as handle:
        json.dump(index, handle, indent=2)

    total = sum(
        os.path.getsize(os.path.join(OUT_DIR, f)) for f in os.listdir(OUT_DIR)
    )
    print(f"\nWrote {len(index)} companies + index to {OUT_DIR}  ({total/1024:.0f} KB total)")


if __name__ == "__main__":
    main()
