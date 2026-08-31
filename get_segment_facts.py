"""
Extract per-segment quarterly financials for Redwood Trust (RWT) from SEC filings.

Why this script exists separately from get_company_facts.py:

    get_company_facts.py calls the CompanyFacts API, which returns *consolidated*
    figures only - one number per concept per period for the whole company.
    Segment breakdowns are "dimensional" facts: they live in each filing's own
    XBRL instance document, tagged against us-gaap:StatementBusinessSegmentsAxis.

    That means a different shape of work. Instead of one API call, we discover
    every 10-Q/10-K, download each filing's instance document, and read the
    facts out of it. Each filing carries only its own period plus prior-year
    comparatives, so the series has to be stitched across filings.

Instance documents are ~5 MB each, so they are cached to disk on first download
and never re-fetched. Only new filings cost a request.
"""

import csv
import os
import re
import time
from collections import defaultdict
from datetime import date

import requests
from lxml import etree

from ingest.edgar import client, xbrl

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CIK = "0000930236"
CACHE_DIR = client.CACHE_DIR

# Kept for the other scripts that import it. New code should go through
# ingest.edgar.client, which rate-limits every SEC request from one place
# rather than relying on each caller to sleep politely.
HEADERS = {"User-Agent": client.user_agent()}

# Only filings from this date forward use the current segment taxonomy
# (Sequoia / CoreVest / Aspire / Redwood Investments / Legacy Investments).
# Earlier filings report a genuinely different set of segments - see the
# "segment taxonomy" note in CLAUDE.md.
EARLIEST_FILING = "2025-01-01"

# XBRL namespaces. The us-gaap namespace URI changes every year
# (http://fasb.org/us-gaap/2025, /2026, ...) so we never hardcode it -
# we resolve prefixes from each document's own namespace map instead.
NS_XBRLI = "http://www.xbrl.org/2003/instance"
NS_XBRLDI = "http://xbrl.org/2006/xbrldi"

SEGMENT_AXIS = "StatementBusinessSegmentsAxis"
CONSOLIDATION_AXIS = "ConsolidationItemsAxis"

# The 22 line items tagged per segment, in income-statement order.
# Keys are the XBRL concept local names; values are the human labels used
# in the CSV output.
LINE_ITEMS = {
    "InterestAndDividendIncomeOperating": "interest_income",
    "InterestExpenseOperating": "interest_expense",
    "InterestIncomeExpenseNet": "net_interest_income",
    "MortgageBankingActivitiesNetExcludingRiskManagementDerivatives": "mortgage_banking_ex_derivatives",
    "MortgageBankingActivitiesNetRiskManagementDerivatives": "mortgage_banking_derivatives",
    "MortgageBankingActivitiesNet": "mortgage_banking_net",
    "UnrealizedGainLossOnInvestments": "investment_fair_value_changes",
    "HEIFairValueChangesNet": "hei_income_net",
    "ServicingIncomeNet": "servicing_income_net",
    "FeeIncomeLossNet": "fee_income_net",
    "OtherOperatingIncomeExpenseNet": "other_operating_income",
    "RealizedInvestmentGainsLosses": "realized_gains_losses",
    "NoninterestIncomeNet": "noninterest_income_net",
    "GeneralAndAdministrativeExpense": "general_and_administrative",
    "PortfolioManagementCosts": "portfolio_management_costs",
    "LoanAcquisitionCosts": "loan_acquisition_costs",
    "OtherExpenses": "other_expenses",
    "IncomeTaxExpenseBenefit": "income_tax",
    "NetIncomeLoss": "segment_contribution",
    "RedeemablePreferredStockDividends": "preferred_dividends",
    "NetIncomeLossAvailableToCommonStockholdersBasicAdjusted": "net_income_to_common",
    "Assets": "segment_assets",
}

# Assets is an instant (point-in-time) measure; everything else is a duration.
INSTANT_ITEMS = {"segment_assets"}


# ---------------------------------------------------------------------------
# Step 1 - discover which filings to read
# ---------------------------------------------------------------------------


def discover_filings():
    """Return [(accession, filing_date, form, primary_doc), ...], newest first."""
    url = f"https://data.sec.gov/submissions/CIK{CIK}.json"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    recent = response.json()["filings"]["recent"]

    filings = []
    for accn, filed, form, doc in zip(
        recent["accessionNumber"],
        recent["filingDate"],
        recent["form"],
        recent["primaryDocument"],
    ):
        if form in ("10-Q", "10-K") and filed >= EARLIEST_FILING:
            filings.append((accn, filed, form, doc))
    return filings


# ---------------------------------------------------------------------------
# Step 2 - fetch instance documents, caching to disk
# ---------------------------------------------------------------------------


def instance_path(accession, filing_date, primary_doc):
    """Local cache path for one filing's XBRL instance document."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{filing_date}_{accession}.xml")


def fetch_instance(accession, filing_date, primary_doc):
    """Download the instance document unless we already have it cached.

    The instance is the primary document's filename with .htm swapped for
    _htm.xml - e.g. rwt-20260630.htm -> rwt-20260630_htm.xml. That file is the
    "extracted instance": the same facts as the inline-XBRL filing, but as
    plain XML with signs already normalised.

    Filed documents never change, so once fetched a copy is reused forever.
    """
    instance_name = primary_doc.replace(".htm", "_htm.xml")
    url = client.archive_url(CIK, accession, instance_name)
    return client.cached_get(
        url, f"{filing_date}_{accession}.xml", binary=True, timeout=180
    )


# ---------------------------------------------------------------------------
# Step 3 - turn XBRL contexts into (segment, period) pairs
# ---------------------------------------------------------------------------


def period_to_frame(start, end, instant):
    """Delegates to ingest.edgar.xbrl, where the shared version lives."""
    return xbrl.period_to_frame(start, end, instant)


def parse_contexts(root, prefix_of=None):
    """Map context id -> (segment_name, frame).

    Delegates to ingest.edgar.xbrl.segment_contexts, which is where the
    shared version lives. The `prefix_of` argument is unused and kept only so
    existing callers do not break.
    """
    return xbrl.segment_contexts(root)


# ---------------------------------------------------------------------------
# Step 4 - read the facts themselves
# ---------------------------------------------------------------------------


def extract_facts(path):
    """Return [(segment, frame, line_item, value), ...] for one filing.

    The parsing itself lives in ingest.edgar.xbrl so other companies reuse it;
    what stays here is the RWT-specific choice of which 22 line items matter
    and what to call them.
    """
    root = xbrl.parse(path)
    contexts = xbrl.segment_contexts(root)
    if not contexts:
        return []

    results = []
    for context_ref, name, value in xbrl.facts_for_contexts(root, contexts, set(LINE_ITEMS)):
        segment, frame = contexts[context_ref]
        results.append((segment, frame, LINE_ITEMS[name], value))
    return results


# ---------------------------------------------------------------------------
# Step 5 - derive Q4 from the annual figure
# ---------------------------------------------------------------------------


def derive_q4(records, structure_of):
    """Fill in Q4 as Annual - Q1 - Q2 - Q3 for duration line items.

    Same arithmetic as extract_quarterly_duration_kpi() in
    get_company_facts.py - 10-Qs report Q1/Q2/Q3 directly and the 10-K reports
    only the full year, so Q4 has to be backed out. Instant measures (assets)
    are tagged at every quarter-end already and need no derivation.

    The extra rule here, which the consolidated version does not need: all four
    inputs must come from filings reporting the SAME set of segments.

    Redwood has redrawn its segments repeatedly. Subtracting quarters reported
    under one structure from an annual reported under another produces a number
    that looks plausible and is wrong - the FY2025 annual predates the Aspire
    segment, while Q1 and Q2 2025 were later restated to include it, so a naive
    subtraction silently buries Aspire's result inside someone else's Q4. Where
    the structures disagree we skip the derivation and leave the quarter empty.
    """
    derived = {}
    skipped = set()

    by_segment_item = defaultdict(dict)
    for (segment, frame, item), value in records.items():
        by_segment_item[(segment, item)][frame] = value

    for (segment, item), frames in by_segment_item.items():
        if item in INSTANT_ITEMS:
            continue
        for frame, annual in frames.items():
            if not re.fullmatch(r"CY\d{4}", frame):
                continue
            year = frame[2:6]
            quarters = [f"CY{year}Q{n}" for n in (1, 2, 3)]
            if not all(q in frames for q in quarters):
                continue
            q4 = f"CY{year}Q4"
            if q4 in frames:
                continue

            structures = {structure_of[(segment, frame, item)]}
            structures |= {structure_of[(segment, q, item)] for q in quarters}
            if len(structures) > 1:
                skipped.add((year, item))
                continue

            derived[(segment, q4, item)] = annual - sum(
                frames[q] for q in quarters
            )

    return derived, skipped


# ---------------------------------------------------------------------------
# Step 6 - export
# ---------------------------------------------------------------------------


def quarter_sort_key(frame):
    """Delegates to ingest.edgar.xbrl."""
    return xbrl.quarter_sort_key(frame)


def export_long(records, sources, filed_of, structure_of, filename):
    """Tidy long-format CSV: one row per segment/quarter/line item.

    Carries full provenance - which filing the number came from, and how many
    segments that filing reported - so a reader can tell whether two rows are
    actually comparable.
    """
    rows = []
    for key, value in records.items():
        segment, frame, item = key
        label = frame[:-1] if frame.endswith("I") else frame
        rows.append(
            {
                "quarter": label,
                "segment": segment,
                "line_item": item,
                "value": round(value, 2),
                "source": sources.get(key, "reported"),
                "filed": filed_of.get(key, ""),
                "segment_structure": structure_of.get(key, ""),
            }
        )

    rows.sort(key=lambda r: (quarter_sort_key(r["quarter"]), r["segment"], r["line_item"]))

    with open(filename, "w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "quarter", "segment", "line_item", "value",
                "source", "filed", "segment_structure",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def export_wide(records, structure_of, item, filename, current_structure=None):
    """Chart-ready wide CSV: one row per quarter, one column per segment.

    When current_structure is given, only quarters reported under that segment
    structure are written. Mixing structures in a chart would draw a line that
    silently changes meaning partway along, so the default for plotting is the
    consistent subset.
    """
    grid = defaultdict(dict)
    segments = set()
    for key, value in records.items():
        segment, frame, line_item = key
        if line_item != item:
            continue
        if current_structure is not None and structure_of.get(key) != current_structure:
            continue
        label = frame[:-1] if frame.endswith("I") else frame
        grid[label][segment] = value
        segments.add(segment)

    segments = sorted(segments)
    quarters = sorted(grid, key=quarter_sort_key)

    with open(filename, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["quarter"] + segments)
        for frame in quarters:
            writer.writerow(
                [frame] + [grid[frame].get(seg, "") for seg in segments]
            )
    return len(quarters), segments


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 78)
    print("RWT SEGMENT EXTRACTION")
    print("=" * 78)

    print("\nStep 1 - discovering filings")
    filings = discover_filings()
    print(f"  {len(filings)} filings on or after {EARLIEST_FILING}:")
    for accn, filed, form, _ in filings:
        print(f"    {form:5}  filed {filed}  {accn}")

    print("\nStep 2 - fetching instance documents (cached after first run)")
    paths = []
    for accn, filed, form, doc in filings:
        path, downloaded = fetch_instance(accn, filed, doc)
        size = os.path.getsize(path) / 1_000_000
        print(f"    {'downloaded' if downloaded else 'cached    '}  {filed}  {size:5.1f} MB")
        paths.append((accn, filed, form, path))
        if downloaded:
            time.sleep(0.4)  # stay well inside the SEC's rate limit

    print("\nStep 3-4 - parsing segment facts")
    # Latest filing wins for any (segment, frame, line_item) reported more
    # than once - restatements and conformed comparatives beat originals.
    records = {}
    filed_of = {}
    structure_of = {}
    taxonomy = {}

    for accn, filed, form, path in sorted(paths, key=lambda p: p[1]):
        facts = extract_facts(path)
        segments = sorted({segment for segment, _, _, _ in facts})
        taxonomy[filed] = segments
        # A short signature for "which segments did this filing report" -
        # used to keep incomparable periods from being mixed.
        signature = "+".join(s[:4] for s in segments)
        print(f"    {filed}  {len(facts):4} facts  {len(segments)} segments")

        for segment, frame, item, value in facts:
            key = (segment, frame, item)
            if key not in filed_of or filed >= filed_of[key]:
                records[key] = value
                filed_of[key] = filed
                structure_of[key] = signature

    current_structure = structure_of[
        max(structure_of, key=lambda k: filed_of[k])
    ]

    print("\nStep 5 - deriving Q4 from annual figures")
    derived, skipped = derive_q4(records, structure_of)
    sources = {}
    for key, value in derived.items():
        records[key] = value
        sources[key] = "derived (Annual - Q1 - Q2 - Q3)"
        filed_of[key] = filed_of[(key[0], f"CY{key[1][2:6]}", key[2])]
        structure_of[key] = structure_of[(key[0], f"CY{key[1][2:6]}", key[2])]
    print(f"    {len(derived)} derived")
    if skipped:
        years = sorted({year for year, _ in skipped})
        print(f"    skipped Q4 for {', '.join(years)} - the annual and the")
        print("      quarters were reported under different segment structures,")
        print("      so the subtraction would not be meaningful")

    # Drop the bare annual frames now that Q4 has been backed out of them -
    # the CSVs are a quarterly series, not a mix of quarters and years.
    for key in [k for k in records if re.fullmatch(r"CY\d{4}", k[1])]:
        del records[key]

    print("\nStep 6 - exporting")
    n = export_long(records, sources, filed_of, structure_of,
                    "rwt_segment_quarterly.csv")
    print(f"    rwt_segment_quarterly.csv         {n} rows (all structures, with provenance)")

    n, segs = export_wide(records, structure_of, "segment_contribution",
                          "rwt_segment_contribution.csv", current_structure)
    print(f"    rwt_segment_contribution.csv      {n} quarters x {len(segs)} segments")

    n, segs = export_wide(records, structure_of, "segment_assets",
                          "rwt_segment_assets.csv", current_structure)
    print(f"    rwt_segment_assets.csv            {n} quarters x {len(segs)} segments")

    print("\nSegment structure by filing (Redwood has redrawn these repeatedly):")
    for filed in sorted(taxonomy):
        print(f"    {filed}: {', '.join(taxonomy[filed])}")

    print("\nDone.")


if __name__ == "__main__":
    main()
