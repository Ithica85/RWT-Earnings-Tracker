"""
Restructuring and governance signals from 8-K item codes.

An 8-K is the filing a company makes when something material happens between
quarterly reports, and each one is tagged with numeric item codes saying what
kind of event it was. Those codes are exposed in the free submissions feed, so
this works for every public filer with no per-company configuration at all.

Why this is the right shape for the "will there be a re-org" question:

    Item 2.05 is filed when a company COMMITS to an exit or disposal plan -
    which is what a restructuring is, in the SEC's language. It is not a
    rumour or a forecast; it is a dated legal disclosure with the estimated
    costs attached.

    So this module publishes no predictions and computes no probability. It
    surfaces what companies were required to tell the public, with dates and
    links, and lets the reader draw the conclusion. A probability attached to
    a named employer would be indefensible when wrong; a filing record is
    simply true.

Absence is informative too. Redwood expensed ~$7M of severance in Q1 2026
without filing a 2.05, which tells you the restructuring was handled inside
normal operations rather than as a committed exit plan - a meaningfully
smaller thing.
"""

import csv
import sys

from ingest.edgar import client

# Item codes worth surfacing, with what they actually mean to someone deciding
# whether to work somewhere. Codes not listed here are routine filings -
# earnings releases, Reg FD disclosures, exhibit attachments - and are ignored.
ITEMS = {
    # --- direct employment signals -----------------------------------------
    "1.03": ("Bankruptcy or receivership", "high"),
    "2.05": ("Committed to an exit or disposal plan (restructuring)", "high"),
    # 5.02 is deliberately NOT high severity. The same item code covers a CFO
    # resigning under pressure and a new independent director being elected -
    # the code alone cannot tell them apart, and treating every one as a
    # warning would cry wolf on routine board housekeeping. Separating them
    # requires reading the filing body for "resigned" / "terminated" versus
    # "appointed" / "elected", which is a text-parsing job this collector
    # does not do. Until it does, this stays medium and says so.
    "5.02": ("Director or senior officer change (departure OR appointment)", "medium"),
    # --- financial distress signals ----------------------------------------
    "2.06": ("Material asset impairment", "medium"),
    "3.01": ("Delisting notice or listing-rule failure", "medium"),
    "4.01": ("Changed auditors", "medium"),
    "4.02": ("Prior financial statements no longer reliable", "medium"),
    # --- structural change --------------------------------------------------
    "5.01": ("Change of control of the company", "medium"),
    "2.01": ("Completed an acquisition or disposal of assets", "medium"),
    "2.04": ("Event accelerating a debt obligation", "medium"),
}

SEVERITY_ORDER = {"high": 0, "medium": 1}


def collect(cik, since=None):
    """Return signal rows for one company, newest first.

    One row per (filing, notable item) pair - a single 8-K can carry several
    item codes, and each is a separate signal.
    """
    rows = []
    for filing in client.filings(cik, forms={"8-K"}, since=since):
        if not filing["items"]:
            continue
        for code in [c.strip() for c in filing["items"].split(",")]:
            if code not in ITEMS:
                continue
            meaning, severity = ITEMS[code]
            rows.append(
                {
                    "date": filing["filed"],
                    "item": code,
                    "meaning": meaning,
                    "severity": severity,
                    "accession": filing["accession"],
                    "url": client.archive_url(
                        cik, filing["accession"], filing["primary_document"]
                    ),
                }
            )
    rows.sort(key=lambda r: (r["date"], SEVERITY_ORDER[r["severity"]]), reverse=True)
    return rows


def collect_many(tickers, since=None):
    """Collect signals for several companies, keyed by ticker."""
    results = {}
    for ticker in tickers:
        cik, name = client.ticker_to_cik(ticker)
        results[ticker] = {
            "cik": cik,
            "name": name,
            "signals": collect(cik, since=since),
        }
    return results


def export(results, path):
    """Write all companies' signals to one CSV."""
    fields = ["ticker", "company", "date", "item", "meaning", "severity", "accession", "url"]
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for ticker, data in results.items():
            for row in data["signals"]:
                writer.writerow({"ticker": ticker, "company": data["name"], **row})


def main():
    tickers = sys.argv[1:] or ["RWT", "NLY", "AGNC", "PMT", "MFA"]
    since = "2024-01-01"

    print("=" * 78)
    print(f"8-K SIGNAL COLLECTION  (filed on or after {since})")
    print("=" * 78)

    results = collect_many(tickers, since=since)

    for ticker, data in results.items():
        signals = data["signals"]
        counts = {"high": 0, "medium": 0}
        for signal in signals:
            counts[signal["severity"]] += 1
        print(f"\n{ticker} - {data['name']}  (CIK {data['cik']})")
        print(f"  {len(signals)} notable: {counts['high']} high, {counts['medium']} medium")

        restructuring = [s for s in signals if s["item"] == "2.05"]
        if restructuring:
            for signal in restructuring:
                print(f"    ** {signal['date']}  ITEM 2.05  {signal['meaning']}")
        else:
            print("    no item 2.05 - no committed exit or disposal plan disclosed")

        for signal in signals[:4]:
            print(f"    {signal['date']}  {signal['item']}  {signal['meaning']}")

    path = "signals_eight_k.csv"
    export(results, path)
    total = sum(len(d["signals"]) for d in results.values())
    print(f"\nExported {total} signals across {len(results)} companies to {path}")


if __name__ == "__main__":
    main()
