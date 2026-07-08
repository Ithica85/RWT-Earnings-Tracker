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
| `get_company_facts.py` | Main script — single SEC API fetch, extracts EPS (derives missing Q4 values) and book value per share, exports CSVs |
| `plot_eps.py` | Reads `rwt_quarterly_eps_complete.csv` and renders a bar chart to `rwt_eps_chart.png` (no API call) |
| `plot_bvps.py` | Reads `rwt_quarterly_bvps.csv` and renders a line chart to `rwt_bvps_chart.png` (no API call) |
| `rwt_quarterly_eps.csv` | One row per reported quarter of diluted EPS (Q1–Q3 only; SEC doesn't tag a standalone Q4 frame) |
| `rwt_quarterly_eps_complete.csv` | Same data plus derived Q4 values, with a `source` column distinguishing reported vs. derived |
| `rwt_quarterly_bvps.csv` | One row per quarter of book value per common share, computed from balance-sheet data |
| `rwt_eps_chart.png` | Output of `plot_eps.py` — quarterly EPS bar chart |
| `rwt_bvps_chart.png` | Output of `plot_bvps.py` — quarterly BVPS line chart |

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
11. Extracts `StockholdersEquity`, `CommonStockSharesOutstanding`, and `PreferredStockValue` (all balance-sheet "instant" concepts, already tagged for every quarter including Q4 — no derivation needed), computes book value per common share as `(StockholdersEquity - PreferredStockValue) / CommonStockSharesOutstanding`, and exports to `rwt_quarterly_bvps.csv`

## What plot_eps.py does

Reads `rwt_quarterly_eps_complete.csv` (does not call the SEC API) and renders a bar chart to `rwt_eps_chart.png`:

1. Colors each bar green (positive EPS) or red (negative EPS) so the profit/loss trend reads at a glance
2. Hatches derived Q4 bars so they're visually distinguishable from SEC-reported values
3. Checks whether the largest-magnitude quarter dwarfs the rest (e.g. CY2020Q1's COVID write-down of -8.28) — if so, clips the y-axis to the bulk of the data and annotates the clipped bar with its real value, so one outlier doesn't flatten every other quarter

## What plot_bvps.py does

Reads `rwt_quarterly_bvps.csv` (does not call the SEC API) and renders a line chart to `rwt_bvps_chart.png`:

1. Single-hue line (BVPS is a magnitude trending over time, not a profit/loss series that crosses zero, so it gets a sequential color rather than EPS's red/green split)
2. Direct-labels only the most recent quarter's value — not every point — per the project's charting convention of sparing labels
3. No legend needed — a single series is already named by the chart title

## How to run

```
python3 get_company_facts.py
python3 plot_eps.py
python3 plot_bvps.py
```

Requires the `requests` and `matplotlib` libraries. Install them with:

```
pip3 install requests matplotlib
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
- **Instant vs. duration frames:** Balance-sheet concepts (`StockholdersEquity`, `CommonStockSharesOutstanding`, `PreferredStockValue`) are point-in-time ("instant") measures, tagged with frames ending in `I` (e.g. `CY2025Q4I`) rather than EPS's duration frames (e.g. `CY2025Q4`). Because they're snapshots at each quarter-end, the SEC tags Q4 directly — no derivation step like EPS needs.
- **BVPS uses common equity, not total equity:** RWT carries preferred stock on its balance sheet (~$66.9M as of 2023+), and preferred holders don't share in common book value. BVPS is computed as `(StockholdersEquity - PreferredStockValue) / CommonStockSharesOutstanding`, not `StockholdersEquity / CommonStockSharesOutstanding`.

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

`rwt_quarterly_bvps.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q4`) |
| `book_value_per_share` | `(StockholdersEquity - PreferredStockValue) / CommonStockSharesOutstanding`, rounded to 2dp |
| `stockholders_equity` | Total stockholders' equity in USD, as of quarter-end |
| `preferred_stock_value` | Preferred stock value in USD, as of quarter-end (0 if none outstanding) |
| `shares_outstanding` | Common shares outstanding as of quarter-end |
| `filed` | Date the source filing was submitted to SEC |
| `form` | Form type (`10-Q` or `10-K`) |

## Next steps (not yet built)

- Extract additional KPIs beyond EPS and book value (e.g. dividends, net interest income)
- Filter to a specific date range
- Interactive UI (e.g. Streamlit) if static charts stop being enough
