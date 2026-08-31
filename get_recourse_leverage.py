"""
Build a recourse leverage ratio for Redwood Trust (RWT).

Why this KPI exists:

    rwt_quarterly_debt_to_equity.csv reports gross debt-to-equity - total
    liabilities over stockholders' equity - which reached 29.9x in CY2026Q2.
    Read literally that implies extreme distress, and it is misleading.

    Redwood consolidates securitisation entities onto its balance sheet under
    GAAP. Creditors of those entities have no claim on Redwood Trust, Inc. -
    if the underlying loans sour, the ABS holders absorb it. So most of that
    ~$28B of liabilities is not an obligation the parent company can be chased
    for. What matters for solvency is RECOURSE debt: borrowings Redwood itself
    is actually on the hook for.

    That figure is not in the XBRL company-facts feed. It comes from two
    places, and this script reads both:

      secured recourse debt   - stated in the MD&A narrative and nowhere else,
                                extracted by regex from the filing text
      corporate debt          - convertible notes, senior notes, trust
                                preferred, promissory notes; XBRL-tagged as
                                DebtInstrumentFaceAmount under the
                                CorporateDebtSecuritiesMember dimension

Reconciliation check (CY2026Q2): secured recourse 3.620B + corporate 0.902B
+ secured non-recourse 0.450B = 4.972B, against an undimensioned total debt
face amount of 4.978B tagged in the same filing. The two paths agree.
"""

import csv
import os
import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup
from lxml import etree

from get_segment_facts import CACHE_DIR, HEADERS, fetch_instance

# Both halves of the calculation only line up from the 2024-08-07 filing
# onward, so there is no point downloading anything earlier:
#
#   - Before that, corporate debt is not tagged under
#     CorporateDebtSecuritiesMember. It appears only as fair-value
#     disclosures (ConvertibleDebtFairValueDisclosures and friends), which
#     is a different measurement basis to the face amounts used later -
#     splicing the two would produce a step in the series that reflects
#     accounting presentation, not borrowing.
#   - The three 2023 10-Qs also say "recourse debt" rather than "secured
#     recourse debt". That unqualified figure appears to already include
#     corporate debt, so adding corporate debt to it would double-count.
#
# The usable window still covers the entire leverage breakout this KPI
# exists to explain: gross debt-to-equity ran 12.5x to 29.9x across it.
EARLIEST_FILING = "2024-06-01"

DOC_CACHE = "sec_cache/text"

NS_XBRLI = "http://www.xbrl.org/2003/instance"
NS_XBRLDI = "http://xbrl.org/2006/xbrldi"

# The MD&A sentence reads, with minor variation between filings:
#   "At June 30, 2026, in aggregate, we had $3.62 billion of secured
#    recourse debt outstanding, financing our mortgage banking platforms..."
SECURED_RECOURSE = re.compile(
    r"we had \$?([\d.,]+)\s*(billion|million)\s*(?:in|of)?\s*secured recourse debt",
    re.IGNORECASE,
)

CORPORATE_DEBT_MEMBER = "CorporateDebtSecuritiesMember"


# ---------------------------------------------------------------------------
# Filing text - for the MD&A figure
# ---------------------------------------------------------------------------


def fetch_document_text(accession, filing_date, primary_doc):
    """Download the filing's primary document and cache it as plain text.

    The XBRL instance holds only tagged facts, and the recourse figure is not
    tagged - it lives in the narrative. So this fetches the human-readable
    document, strips the markup once, and caches the text (~400 KB rather
    than the ~4 MB of inline-XBRL HTML).
    """
    os.makedirs(DOC_CACHE, exist_ok=True)
    path = os.path.join(DOC_CACHE, f"{filing_date}_{accession}.txt")
    if os.path.exists(path):
        return path, False

    url = (
        f"https://www.sec.gov/Archives/edgar/data/930236/"
        f"{accession.replace('-', '')}/{primary_doc}"
    )
    response = requests.get(url, headers=HEADERS, timeout=180)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = re.sub(r"[ \t\xa0]+", " ", soup.get_text(" "))

    with open(path, "w") as handle:
        handle.write(text)
    return path, True


def extract_secured_recourse(text_path):
    """Pull the aggregate secured recourse debt figure out of the MD&A."""
    text = open(text_path).read()
    match = SECURED_RECOURSE.search(text)
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    scale = 1_000_000_000 if match.group(2).lower() == "billion" else 1_000_000
    return amount * scale


# ---------------------------------------------------------------------------
# XBRL - for corporate (unsecured recourse) debt
# ---------------------------------------------------------------------------


def extract_corporate_debt(instance_path, period_end):
    """Sum every corporate debt instrument outstanding at period end.

    Each instrument (7.75% convertible notes, the various senior notes, trust
    preferred, promissory notes) is tagged as DebtInstrumentFaceAmount and
    dimensioned with DebtInstrumentAxis = CorporateDebtSecuritiesMember.
    Selecting on that axis avoids double-counting: a few instruments are also
    tagged a second time under their own axis.
    """
    root = etree.parse(instance_path).getroot()

    wanted = set()
    for ctx in root.iter(f"{{{NS_XBRLI}}}context"):
        members = {}
        for member in ctx.iter(f"{{{NS_XBRLDI}}}explicitMember"):
            axis = member.get("dimension", "").split(":")[-1]
            members[axis] = (member.text or "").strip().split(":")[-1]

        if members.get("DebtInstrumentAxis") != CORPORATE_DEBT_MEMBER:
            continue

        instant = ctx.find(f"{{{NS_XBRLI}}}period/{{{NS_XBRLI}}}instant")
        if instant is None or instant.text.strip() != period_end.isoformat():
            continue
        wanted.add(ctx.get("id"))

    total = 0
    seen = set()
    for element in root.iter():
        if etree.QName(element).localname != "DebtInstrumentFaceAmount":
            continue
        context_ref = element.get("contextRef")
        if context_ref not in wanted or context_ref in seen:
            continue
        try:
            total += float(element.text.strip())
        except (AttributeError, ValueError):
            continue
        seen.add(context_ref)

    return total if total else None


# ---------------------------------------------------------------------------
# Equity - reuse what get_company_facts.py already extracted
# ---------------------------------------------------------------------------


def load_equity():
    """quarter -> stockholders' equity, from the debt-to-equity CSV."""
    equity = {}
    try:
        with open("rwt_quarterly_debt_to_equity.csv") as handle:
            for row in csv.DictReader(handle):
                equity[row["quarter"]] = float(row["stockholders_equity"])
    except FileNotFoundError:
        print("  ! rwt_quarterly_debt_to_equity.csv not found -")
        print("    run get_company_facts.py first")
    return equity


def frame_for(period_end):
    quarter = (period_end.month - 1) // 3 + 1
    return f"CY{period_end.year}Q{quarter}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 78)
    print("RWT RECOURSE LEVERAGE")
    print("=" * 78)

    print("\nStep 1 - discovering filings")
    url = f"https://data.sec.gov/submissions/CIK0000930236.json"
    recent = requests.get(url, headers=HEADERS, timeout=30).json()["filings"]["recent"]
    filings = [
        (accn, filed, form, doc)
        for accn, filed, form, doc in zip(
            recent["accessionNumber"], recent["filingDate"],
            recent["form"], recent["primaryDocument"],
        )
        if form in ("10-Q", "10-K") and filed >= EARLIEST_FILING
    ]
    print(f"  {len(filings)} filings on or after {EARLIEST_FILING}")

    equity_by_frame = load_equity()

    print("\nStep 2-4 - extracting recourse debt per filing")
    print(f"  {'period':10} {'secured (MD&A)':>17} {'corporate (XBRL)':>18} {'total':>15}")

    rows = []
    for accn, filed, form, doc in sorted(filings, key=lambda f: f[1]):
        # rwt-20260630.htm -> 2026-06-30
        stamp = re.search(r"(\d{8})", doc)
        if not stamp:
            continue
        period_end = date(
            int(stamp.group(1)[:4]), int(stamp.group(1)[4:6]), int(stamp.group(1)[6:])
        )

        text_path, downloaded_text = fetch_document_text(accn, filed, doc)
        if downloaded_text:
            time.sleep(0.4)
        instance_path, downloaded_xml = fetch_instance(accn, filed, doc)
        if downloaded_xml:
            time.sleep(0.4)

        secured = extract_secured_recourse(text_path)
        corporate = extract_corporate_debt(instance_path, period_end)

        if secured is None:
            print(f"  {frame_for(period_end):10} {'no MD&A match':>17}  (skipped)")
            continue

        # Never treat a missing corporate figure as zero - that would silently
        # understate recourse debt by ~$0.9B and flatter the ratio.
        if corporate is None:
            print(
                f"  {frame_for(period_end):10} {secured/1e9:>16.2f}B "
                f"{'not tagged':>18}  (skipped)"
            )
            continue

        total = secured + corporate
        rows.append(
            {
                "quarter": frame_for(period_end),
                "secured_recourse_debt": int(secured),
                "corporate_debt": int(corporate) if corporate else "",
                "total_recourse_debt": int(total),
                "filed": filed,
                "form": form,
            }
        )
        print(
            f"  {frame_for(period_end):10} {secured/1e9:>16.2f}B "
            f"{(corporate or 0)/1e9:>17.2f}B {total/1e9:>14.2f}B"
        )

    print("\nStep 5 - computing the ratio against stockholders' equity")
    print(f"  {'quarter':10} {'recourse debt':>15} {'equity':>13} {'recourse':>10} {'gross':>9}")

    gross = {}
    try:
        with open("rwt_quarterly_debt_to_equity.csv") as handle:
            gross = {r["quarter"]: float(r["debt_to_equity"]) for r in csv.DictReader(handle)}
    except FileNotFoundError:
        pass

    output = []
    for row in rows:
        equity = equity_by_frame.get(row["quarter"])
        if not equity:
            print(f"  {row['quarter']:10}  no equity figure - skipped")
            continue
        ratio = row["total_recourse_debt"] / equity
        row["stockholders_equity"] = int(equity)
        row["recourse_leverage"] = round(ratio, 2)
        row["gross_debt_to_equity"] = gross.get(row["quarter"], "")
        output.append(row)
        print(
            f"  {row['quarter']:10} {row['total_recourse_debt']/1e9:>14.2f}B "
            f"{equity/1e9:>12.2f}B {ratio:>9.2f}x "
            f"{row['gross_debt_to_equity'] or 0:>8.2f}x"
        )

    fields = [
        "quarter", "recourse_leverage", "gross_debt_to_equity",
        "total_recourse_debt", "secured_recourse_debt", "corporate_debt",
        "stockholders_equity", "filed", "form",
    ]
    with open("rwt_quarterly_recourse_leverage.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in output:
            writer.writerow({k: row.get(k, "") for k in fields})

    print(f"\nExported {len(output)} quarters to rwt_quarterly_recourse_leverage.csv")
    if output:
        last = output[-1]
        print(
            f"\n  {last['quarter']}: recourse leverage {last['recourse_leverage']}x "
            f"vs gross debt-to-equity {last['gross_debt_to_equity']}x"
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
