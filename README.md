# RWT — SEC Filing KPI Extraction Project

## Project goal

Extract financial KPIs for Redwood Trust (NYSE: RWT) from the SEC EDGAR API and analyse them. The long-term aim is to build a reusable script that pulls key metrics from SEC filings and outputs structured data for analysis.

## Company

- **Name:** Redwood Trust Inc
- **Ticker:** RWT
- **CIK:** 0000930236 (SEC unique identifier, zero-padded to 10 digits)

## SEC API

- **Endpoint used:** `https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json`
- **Auth:** None required, but the SEC mandates a `User-Agent` header identifying the requester (email address)
- **Data format:** JSON. Top-level keys are `cik`, `entityName`, `facts`
- **Taxonomy:** Financial data lives under `facts > us-gaap`. RWT reports 612 US-GAAP concepts.
- **Rate limiting:** Avoid making multiple calls to the same endpoint in one script run

## Files

| File | Description |
|------|-------------|
| `get_company_facts.py` | Main script — single SEC API fetch, extracts EPS, derives missing Q4 values, exports both CSVs |
| `rwt_quarterly_eps.csv` | One row per reported quarter of diluted EPS (Q1–Q3 only; SEC doesn't tag a standalone Q4 frame) |
| `rwt_quarterly_eps_complete.csv` | Same data plus derived Q4 values, with a `source` column distinguishing reported vs. derived |

## What get_company_facts.py does

1. Fetches the full CompanyFacts JSON for RWT from the SEC API (one call total)
2. Prints top-level structure and company name to confirm the response
3. Lists all US-GAAP concepts (612 total) and searches by keyword (`earn`, `share`, `income`, `net`)
4. Safely extracts `EarningsPerShareDiluted` — checks the concept exists before accessing it, and prints alternatives if not found
5. Prints the EPS data structure (`label`, `description`, `units`)
6. Shows the first 5 and most recent 10 raw EPS records
7. Deduplicates by latest-filed value, keeping every framed record (quarterly *and* annual — the annual figure is needed in step 9)
8. Filters to quarterly records (frames containing `"Q"`, e.g. `CY2025Q1`), sorts chronologically by frame string, prints quarter-over-quarter % change, and exports to `rwt_quarterly_eps.csv`
9. The SEC never tags a standalone Q4 frame for EPS, so for each year where Q1, Q2, Q3, and the annual figure are all present, derives Q4 as `Annual - Q1 - Q2 - Q3`
10. Merges reported + derived quarters, prints each with a `<- derived` flag where applicable, and exports to `rwt_quarterly_eps_complete.csv` with a `source` column

## How to run

```
python3 get_company_facts.py
```

Requires the `requests` library. Install it with:

```
pip3 install requests
```

## EPS record structure

Each record returned by the SEC API looks like:

```python
{
  "start":  "2025-01-01",   # period start date
  "end":    "2025-03-31",   # period end date
  "val":    0.10,           # EPS value in USD/share
  "accn":   "0000930236-26-000020",  # SEC accession number (unique filing ID)
  "fy":     2026,           # fiscal year of the filing
  "fp":     "Q1",           # fiscal period (FY, Q1, Q2, Q3, Q4)
  "form":   "10-Q",         # form type (10-K = annual, 10-Q = quarterly)
  "filed":  "2026-05-07",   # date filed with SEC
  "frame":  "CY2026Q1"      # standardised calendar period label (not always present)
}
```

## Key design decisions

- **Deduplication by latest filing:** The SEC stores every version of a reported figure. The script keeps the most recently filed value per quarter frame, so restatements and corrections win over originals.
- **`record.get("frame")`** instead of `record["frame"]` — avoids a `KeyError` crash on records that have no frame field.
- **QoQ % change edge cases:** Sign flips (EPS crosses zero between quarters) and zero prior-quarter values are flagged as `N/A` rather than printing a misleading percentage.
- **Dynamic unit detection:** `unit_name = list(eps["units"].keys())[0]` picks the unit type automatically rather than hardcoding `"USD/shares"`, making the pattern reusable for other concepts.
- **Derived Q4:** SEC frames don't include a standalone Q4 for EPS, so Q4 is backed out as `Annual - Q1 - Q2 - Q3` whenever all four inputs are available for a year. Every derived row is tagged in the `source` column so it's never confused with an SEC-reported figure.

## CSV output columns

`rwt_quarterly_eps.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q1`) |
| `eps` | Diluted EPS in USD/share |
| `filed` | Date the source filing was submitted to SEC |
| `form` | Form type (`10-Q` or `10-K`) |

`rwt_quarterly_eps_complete.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q4`) |
| `eps` | Diluted EPS in USD/share (reported or derived) |
| `source` | `reported` (direct from an SEC frame) or `derived (Annual - Q1 - Q2 - Q3)` |

## Next steps (not yet built)

- Extract additional KPIs beyond EPS (e.g. book value, dividends, net interest income)
- Filter to a specific date range
- Build trend analysis or visualisation on top of the CSV
