"""
Build a quarterly operating expenses series for Redwood Trust (RWT).

Why this needs its own script rather than a line in get_company_facts.py:

    The us-gaap `OperatingExpenses` concept covers CY2009Q2 to CY2024Q2 and
    then stops. Unlike interest expense, no successor concept took over - the
    filings stopped tagging a total and now tag only the four components:

        GeneralAndAdministrativeExpense   (us-gaap)
        PortfolioManagementCosts          (rwt, custom)
        LoanAcquisitionCosts              (rwt, custom)
        OtherExpenses                     (us-gaap)

    Two of those are Redwood's own custom tags, and the CompanyFacts API
    serves only standard taxonomies (dei, invest, srt, us-gaap, ffd). So the
    recent total cannot be assembled from the API at all - it has to come from
    the filing instance documents, which get_segment_facts.py already caches.

    This script therefore splices two sources:

        CY2009Q2 - CY2024Q2   the tagged OperatingExpenses total (API)
        CY2024Q3 onward       the four components summed (filing instances)

    The splice is verified rather than assumed. On every quarter where both
    methods are available, the component sum must equal the tagged total to
    the dollar; the script fails loudly if any overlap disagrees. Spot checks
    when this was written: CY2023Q2 40,324,000 · CY2024Q1 43,764,000 ·
    CY2024Q2 46,989,000, all exact. The CY2026Q2 component sum of 55,965,000
    also matches the "$56 million" stated in that quarter's MD&A.
"""

import csv
import json
import os
import re
import time
from datetime import date

import requests
from lxml import etree

from get_segment_facts import HEADERS, discover_filings, fetch_instance

FACTS_CACHE = "sec_cache/companyfacts.json"
CSV_PATH = "rwt_quarterly_operating_expenses.csv"

NS_XBRLI = "http://www.xbrl.org/2003/instance"
NS_XBRLDI = "http://xbrl.org/2006/xbrldi"

COMPONENTS = (
    "GeneralAndAdministrativeExpense",
    "PortfolioManagementCosts",
    "LoanAcquisitionCosts",
    "OtherExpenses",
)


# ---------------------------------------------------------------------------
# Source 1 - the tagged total, from the CompanyFacts API
# ---------------------------------------------------------------------------


def load_company_facts():
    """Fetch CompanyFacts once and cache it; later runs read from disk."""
    if os.path.exists(FACTS_CACHE):
        return json.load(open(FACTS_CACHE))
    os.makedirs(os.path.dirname(FACTS_CACHE), exist_ok=True)
    url = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000930236.json"
    response = requests.get(url, headers=HEADERS, timeout=180)
    response.raise_for_status()
    with open(FACTS_CACHE, "w") as handle:
        handle.write(response.text)
    return response.json()


def tagged_totals(facts):
    """frame -> (value, filed, form) from the OperatingExpenses concept.

    Keeps annual frames too - they are needed to derive Q4, same as the
    duration KPIs in get_company_facts.py.
    """
    concept = facts["facts"]["us-gaap"]["OperatingExpenses"]["units"]["USD"]
    best = {}
    for record in concept:
        frame = record.get("frame")
        if not frame or frame.endswith("I"):
            continue
        if frame not in best or record["filed"] > best[frame][1]:
            best[frame] = (record["val"], record["filed"], record.get("form"))
    return best


def repair_negatives(tagged):
    """Handle negative quarters, which operating expenses cannot actually be.

    The SEC data contains sign errors: RWT's 10-K filed 2015-02-25 tagged all
    four quarters of 2013 negative, even though that year's annual figure is
    positive. Left alone they plot as bars below zero, which is nonsense.

    Two cases, treated differently on purpose:

      provable   every quarter of the year is negative AND they sum to exactly
                 minus the annual figure. The magnitudes are right and only the
                 sign is inverted, so the signs are flipped and the rows marked.
      unprovable anything else - e.g. CY2009Q3, an isolated negative in a year
                 whose other quarters are positive and where the sum test
                 cannot run. There is no evidence for what the value should
                 be, so the quarter is dropped rather than guessed at.

    Returns (repaired_tagged, flipped_frames, dropped_frames).
    """
    negatives = {f for f, (value, _, _) in tagged.items()
                 if "Q" in f and value < 0}
    flipped, dropped = [], []

    for year in sorted({f[2:6] for f in negatives}):
        annual = tagged.get(f"CY{year}")
        quarters = [f"CY{year}Q{n}" for n in (1, 2, 3, 4)]
        present = [q for q in quarters if q in tagged]

        provable = (
            annual is not None
            and len(present) == 4
            and all(tagged[q][0] < 0 for q in present)
            and sum(tagged[q][0] for q in present) == -annual[0]
        )

        for quarter in present:
            if tagged[quarter][0] >= 0:
                continue
            if provable:
                value, filed, form = tagged[quarter]
                tagged[quarter] = (-value, filed, form)
                flipped.append(quarter)
            else:
                del tagged[quarter]
                dropped.append(quarter)

    return tagged, flipped, dropped


# ---------------------------------------------------------------------------
# Source 2 - the components, from filing instance documents
# ---------------------------------------------------------------------------


def component_totals(instance_path):
    """period -> summed components, for consolidated (undimensioned) contexts.

    A context with no explicitMember is the company as a whole. Anything
    dimensioned is a segment or other slice and must not be added in, or the
    total would double-count.
    """
    root = etree.parse(instance_path).getroot()

    periods = {}
    for ctx in root.iter(f"{{{NS_XBRLI}}}context"):
        if list(ctx.iter(f"{{{NS_XBRLDI}}}explicitMember")):
            continue
        start = ctx.find(f"{{{NS_XBRLI}}}period/{{{NS_XBRLI}}}startDate")
        end = ctx.find(f"{{{NS_XBRLI}}}period/{{{NS_XBRLI}}}endDate")
        if start is None or end is None:
            continue
        periods[ctx.get("id")] = (
            date.fromisoformat(start.text.strip()),
            date.fromisoformat(end.text.strip()),
        )

    found = {}
    for element in root.iter():
        name = etree.QName(element).localname
        if name not in COMPONENTS:
            continue
        context_ref = element.get("contextRef")
        if context_ref not in periods:
            continue
        try:
            value = int(element.text.strip())
        except (AttributeError, ValueError):
            continue
        found.setdefault(periods[context_ref], {})[name] = value

    # Only accept a period where all four components are present. A partial
    # sum would silently understate the total.
    return {
        period: sum(parts.values())
        for period, parts in found.items()
        if len(parts) == len(COMPONENTS)
    }


def frame_for(start, end):
    """Calendar frame for a duration, or None if it is a YTD stub."""
    span = (end - start).days
    if 80 <= span <= 100:
        return f"CY{end.year}Q{(end.month - 1) // 3 + 1}"
    if 350 <= span <= 380:
        return f"CY{end.year}"
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 78)
    print("RWT OPERATING EXPENSES")
    print("=" * 78)

    print("\nStep 1 - tagged OperatingExpenses total (CompanyFacts API)")
    facts = load_company_facts()
    tagged = tagged_totals(facts)
    tagged, flipped, dropped = repair_negatives(tagged)
    tagged_quarters = sorted(f for f in tagged if "Q" in f)
    print(f"  {len(tagged_quarters)} quarters, {tagged_quarters[0]} -> {tagged_quarters[-1]}")
    print("  (the concept stops there - filings no longer tag a total)")
    if flipped:
        print(f"  sign-corrected {len(flipped)}: {', '.join(flipped)}")
        print("    (tagged negative, but the year's quarters summed to exactly")
        print("     minus the annual figure - magnitudes right, sign inverted)")
    if dropped:
        print(f"  dropped {len(dropped)}: {', '.join(dropped)}")
        print("    (negative with no way to verify the intended value)")

    print("\nStep 2 - component sums (filing instance documents)")
    filings = discover_filings()
    components = {}
    for accn, filed, form, doc in sorted(filings, key=lambda f: f[1]):
        path, downloaded = fetch_instance(accn, filed, doc)
        if downloaded:
            time.sleep(0.4)
        for (start, end), total in component_totals(path).items():
            frame = frame_for(start, end)
            if not frame:
                continue
            if frame not in components or filed >= components[frame][1]:
                components[frame] = (total, filed, form)
    component_quarters = sorted(f for f in components if "Q" in f)
    print(f"  {len(component_quarters)} quarters, {component_quarters[0]} -> {component_quarters[-1]}")

    print("\nStep 3 - verifying the splice on overlapping quarters")
    overlap = sorted(set(tagged) & set(components))
    mismatches = [f for f in overlap if tagged[f][0] != components[f][0]]
    for frame in overlap:
        flag = "ok" if tagged[frame][0] == components[frame][0] else "MISMATCH"
        print(f"  {frame:10} tagged {tagged[frame][0]:>14,}   "
              f"components {components[frame][0]:>14,}   {flag}")
    if mismatches:
        raise SystemExit(
            f"\n{len(mismatches)} overlapping period(s) disagree: {mismatches}.\n"
            "The two sources are measuring different things - do not splice them."
        )
    print(f"  all {len(overlap)} overlapping periods agree to the dollar")

    print("\nStep 4 - splicing, tagged total preferred where available")
    merged = {}
    for frame, (value, filed, form) in components.items():
        merged[frame] = (value, filed, form, "components (G&A + portfolio + acquisition + other)")
    for frame, (value, filed, form) in tagged.items():
        label = ("reported (OperatingExpenses, sign corrected)"
                 if frame in flipped else "reported (OperatingExpenses)")
        merged[frame] = (value, filed, form, label)

    print("\nStep 5 - deriving Q4 where the annual and Q1-Q3 are all present")
    derived = 0
    for year in sorted({int(f[2:6]) for f in merged}):
        annual, q4 = f"CY{year}", f"CY{year}Q4"
        quarters = [f"CY{year}Q{n}" for n in (1, 2, 3)]
        if q4 in merged or annual not in merged:
            continue
        if not all(q in merged for q in quarters):
            continue
        value = merged[annual][0] - sum(merged[q][0] for q in quarters)
        merged[q4] = (value, merged[annual][1], merged[annual][2],
                      "derived (Annual - Q1 - Q2 - Q3)")
        derived += 1
    print(f"  {derived} derived")

    rows = []
    for frame in sorted((f for f in merged if "Q" in f),
                        key=lambda f: (int(f[2:6]), int(f[-1]))):
        value, filed, form, source = merged[frame]
        rows.append({
            "quarter": frame,
            "operating_expenses": int(value),
            "source": source,
            "filed": filed,
            "form": form,
        })

    with open(CSV_PATH, "w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["quarter", "operating_expenses", "source", "filed", "form"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nExported {len(rows)} quarters to {CSV_PATH}")
    print(f"  {rows[0]['quarter']} -> {rows[-1]['quarter']}")
    print("\n  most recent:")
    for row in rows[-4:]:
        print(f"    {row['quarter']}  {row['operating_expenses']:>14,}  {row['source']}")

    print("\nDone.")


if __name__ == "__main__":
    main()
