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
| `get_company_facts.py` | Main script — single SEC API fetch, extracts EPS, book value per share, dividends per share, net interest income, net income, total assets, total liabilities, and debt-to-equity ratio (deriving missing Q4 values via a shared helper for the four duration-measure KPIs), exports CSVs |
| `plot_eps.py` | Reads `rwt_quarterly_eps_complete.csv` and renders a bar chart to `rwt_eps_chart.png` (no API call) |
| `plot_bvps.py` | Reads `rwt_quarterly_bvps.csv` and renders a line chart to `rwt_bvps_chart.png` (no API call) |
| `plot_dividends.py` | Reads `rwt_quarterly_dividends_complete.csv` and renders a bar chart to `rwt_dividends_chart.png` (no API call) |
| `plot_nii.py` | Reads `rwt_quarterly_nii_complete.csv` and renders a bar chart to `rwt_nii_chart.png` (no API call) |
| `plot_net_income.py` | Reads `rwt_quarterly_net_income_complete.csv` and renders a bar chart to `rwt_net_income_chart.png` (no API call) |
| `plot_assets.py` | Reads `rwt_quarterly_assets.csv` and renders a line chart to `rwt_assets_chart.png` (no API call) |
| `plot_liabilities.py` | Reads `rwt_quarterly_liabilities.csv` and renders a line chart to `rwt_liabilities_chart.png` (no API call) |
| `plot_debt_to_equity.py` | Reads `rwt_quarterly_debt_to_equity.csv` and renders a line chart to `rwt_debt_to_equity_chart.png` (no API call) |
| `rwt_quarterly_eps.csv` | One row per reported quarter of diluted EPS (Q1–Q3 only; SEC doesn't tag a standalone Q4 frame) |
| `rwt_quarterly_eps_complete.csv` | Same data plus derived Q4 values, with a `source` column distinguishing reported vs. derived |
| `rwt_quarterly_bvps.csv` | One row per quarter of book value per common share, computed from balance-sheet data |
| `rwt_quarterly_dividends.csv` | One row per reported quarter of dividends per common share (SEC tagged Q4 directly through 2019 only; missing thereafter) |
| `rwt_quarterly_dividends_complete.csv` | Same data plus derived Q4 values (2020+), with a `source` column distinguishing reported vs. derived |
| `rwt_quarterly_nii.csv` | One row per reported quarter of net interest income (Q4 missing from 2020 onward, same gap as EPS) |
| `rwt_quarterly_nii_complete.csv` | Same data plus derived Q4 values, with a `source` column distinguishing reported vs. derived |
| `rwt_quarterly_net_income.csv` | One row per reported quarter of net income (Q4 missing from 2020 onward, same gap as EPS) |
| `rwt_quarterly_net_income_complete.csv` | Same data plus derived Q4 values, with a `source` column distinguishing reported vs. derived |
| `rwt_quarterly_assets.csv` | One row per quarter of total assets, a balance-sheet "instant" measure (tagged every quarter, no derivation needed) |
| `rwt_quarterly_liabilities.csv` | One row per quarter of total liabilities, a balance-sheet "instant" measure (tagged every quarter, no derivation needed) |
| `rwt_quarterly_debt_to_equity.csv` | One row per quarter of debt-to-equity ratio (Total Liabilities / Stockholders' Equity), purely derived from data already extracted — no new SEC concept |
| `rwt_eps_chart.png` | Output of `plot_eps.py` — quarterly EPS bar chart |
| `rwt_bvps_chart.png` | Output of `plot_bvps.py` — quarterly BVPS line chart |
| `rwt_dividends_chart.png` | Output of `plot_dividends.py` — quarterly dividends-per-share bar chart |
| `rwt_nii_chart.png` | Output of `plot_nii.py` — quarterly net interest income bar chart |
| `rwt_net_income_chart.png` | Output of `plot_net_income.py` — quarterly net income bar chart |
| `rwt_assets_chart.png` | Output of `plot_assets.py` — quarterly total assets line chart |
| `rwt_liabilities_chart.png` | Output of `plot_liabilities.py` — quarterly total liabilities line chart |
| `rwt_debt_to_equity_chart.png` | Output of `plot_debt_to_equity.py` — quarterly debt-to-equity ratio line chart |

## What get_company_facts.py does

1. Fetches the full CompanyFacts JSON for RWT from the SEC API (one call total)
2. Prints top-level structure and company name to confirm the response
3. Lists all US-GAAP concepts (612 total) and searches by keyword (`earn`, `share`, `income`, `net`)
4. Safely extracts `EarningsPerShareDiluted` — checks the concept exists before accessing it, and prints alternatives if not found
5. Prints the EPS data structure (`label`, `description`, `units`)
6. Shows the first 5 and most recent 10 raw EPS records
7. Defines `extract_quarterly_duration_kpi()` — a shared helper (used by EPS, dividends, and net interest income below) that dedupes by latest-filed value per frame (keeping every framed record, quarterly *and* annual — the annual figure is needed to derive Q4), filters to quarterly records (frames containing `"Q"`, e.g. `CY2025Q1`), sorts chronologically, exports reported-only quarters to `{csv_stem}.csv`, derives any missing Q4 as `Annual - Q1 - Q2 - Q3`, and exports the merged reported+derived result to `{csv_stem}_complete.csv` with a `source` column
8. Calls it for `EarningsPerShareDiluted` → `rwt_quarterly_eps.csv` / `rwt_quarterly_eps_complete.csv`, with quarter-over-quarter % change printed as an EPS-specific extra step
9. Extracts `StockholdersEquity`, `CommonStockSharesOutstanding`, and `PreferredStockValue` (all balance-sheet "instant" concepts, already tagged for every quarter including Q4 — no derivation needed), computes book value per common share as `(StockholdersEquity - PreferredStockValue) / CommonStockSharesOutstanding`, and exports to `rwt_quarterly_bvps.csv`
10. Calls the shared helper for `CommonStockDividendsPerShareDeclared` → `rwt_quarterly_dividends.csv` / `rwt_quarterly_dividends_complete.csv` (Q4 tagged directly 2010–2019, derived from 2020 onward)
11. Calls the shared helper for `InterestIncomeExpenseNet` → `rwt_quarterly_nii.csv` / `rwt_quarterly_nii_complete.csv` (same Q4 gap as EPS — missing every year from 2020 onward)
12. Calls the shared helper for `NetIncomeLoss` → `rwt_quarterly_net_income.csv` / `rwt_quarterly_net_income_complete.csv` (same Q4 gap as EPS — missing every year from 2020 onward; this is the bottom-line dollar figure EPS is derived from)
13. Extracts `Assets` (total assets, a balance-sheet "instant" concept tagged for every quarter including Q4 — no derivation needed, reusing `latest_instant_by_frame()` from the BVPS section) and exports to `rwt_quarterly_assets.csv`
14. Extracts `Liabilities` (total liabilities, same instant-measure shape as `Assets`) and exports to `rwt_quarterly_liabilities.csv`, to pair with total assets for a leverage view (Assets − Liabilities = Equity)
15. Computes debt-to-equity ratio (Total Liabilities / Stockholders' Equity) purely from data already extracted above — no new SEC concept, no extra API call — and exports to `rwt_quarterly_debt_to_equity.csv`

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

## What plot_dividends.py does

Reads `rwt_quarterly_dividends_complete.csv` (does not call the SEC API) and renders a bar chart to `rwt_dividends_chart.png`:

1. Single-hue bars (dividends per share never go negative, so — like BVPS — no red/green profit/loss split is needed)
2. Hatches derived Q4 bars (2020+) so they're visually distinguishable from SEC-reported values, same convention as `plot_eps.py`

## What plot_nii.py does

Reads `rwt_quarterly_nii_complete.csv` (does not call the SEC API) and renders a bar chart to `rwt_nii_chart.png`:

1. Single-hue bars (net interest income never goes negative for RWT historically, so no red/green profit/loss split is needed)
2. Values are divided by 1,000,000 before plotting so the y-axis reads in whole $M rather than raw dollars
3. Hatches derived Q4 bars so they're visually distinguishable from SEC-reported values, same convention as `plot_eps.py` / `plot_dividends.py`

## What plot_net_income.py does

Reads `rwt_quarterly_net_income_complete.csv` (does not call the SEC API) and renders a bar chart to `rwt_net_income_chart.png`:

1. Colors each bar green (positive) or red (negative), same convention as `plot_eps.py` — net income can go negative (e.g. RWT's 2020 COVID write-down), unlike NII or dividends which never do
2. Values are divided by 1,000,000 before plotting so the y-axis reads in whole $M rather than raw dollars, same convention as `plot_nii.py`
3. Hatches derived Q4 bars so they're visually distinguishable from SEC-reported values
4. Same outlier-clipping logic as `plot_eps.py`: if the largest-magnitude quarter dwarfs the rest (CY2020Q1's -$943.4M COVID write-down), the y-axis is clipped to the bulk of the data and the clipped bar is annotated with its real value

## What plot_assets.py does

Reads `rwt_quarterly_assets.csv` (does not call the SEC API) and renders a line chart to `rwt_assets_chart.png`:

1. Single-hue line, same convention as `plot_bvps.py` (total assets is a magnitude trending over time, not a profit/loss series that crosses zero)
2. Direct-labels only the most recent quarter's value, per the project's charting convention of sparing labels
3. Values are divided by 1,000,000,000 before plotting so the y-axis reads in whole $B rather than raw dollars
4. No hatching for derived Q4 — `Assets` is an instant measure tagged every quarter, so there's nothing derived

## What plot_liabilities.py does

Reads `rwt_quarterly_liabilities.csv` (does not call the SEC API) and renders a line chart to `rwt_liabilities_chart.png`:

1. Same single-hue line style as `plot_assets.py` and `plot_bvps.py`
2. Direct-labels only the most recent quarter's value
3. Values are divided by 1,000,000,000 before plotting so the y-axis reads in whole $B
4. No hatching for derived Q4 — `Liabilities` is an instant measure tagged every quarter, so there's nothing derived

## What plot_debt_to_equity.py does

Reads `rwt_quarterly_debt_to_equity.csv` (does not call the SEC API) and renders a line chart to `rwt_debt_to_equity_chart.png`:

1. Same single-hue line style as `plot_assets.py`, `plot_liabilities.py`, and `plot_bvps.py`
2. Direct-labels only the most recent quarter's value, formatted as a multiple (e.g. `27.0x`)
3. No unit conversion needed — the ratio is already a small dimensionless number

## How to run

```
python3 get_company_facts.py
python3 plot_eps.py
python3 plot_bvps.py
python3 plot_dividends.py
python3 plot_nii.py
python3 plot_net_income.py
python3 plot_assets.py
python3 plot_liabilities.py
python3 plot_debt_to_equity.py
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
- **Dividends share EPS's Q4 gap:** `CommonStockDividendsPerShareDeclared` is a duration measure, and the SEC stopped tagging a standalone Q4 frame for it starting in 2020 (it did tag Q4 directly from 2010–2019) — a coincidental match with EPS's gap, not a related concept. Same derive-from-annual treatment applies.
- **Shared helper for duration KPIs:** EPS, dividends, net interest income (`InterestIncomeExpenseNet`), and net income (`NetIncomeLoss`) all turned out to have the identical shape — a duration measure, deduped by latest filing, with Q4 derived from the annual figure. After the third KPI repeated this exact pattern, the dedup/derive/export logic was extracted into `extract_quarterly_duration_kpi()` rather than copy-pasting a near-identical block each time. BVPS stays separate since it's an instant (not duration) measure with a different shape (no Q4 derivation needed, preferred-stock subtraction instead).
- **Net income can go negative, unlike NII/dividends:** `plot_net_income.py` follows `plot_eps.py`'s red/green sign-based coloring and outlier-clipping convention rather than `plot_nii.py`'s single-hue approach, since RWT has posted quarterly net losses (e.g. -$943M in CY2020Q1).
- **Total Assets reuses the BVPS instant-measure pattern, not the duration helper:** `Assets` is tagged every quarter (frames end in `I`, same as `StockholdersEquity`), so it's extracted with the existing `latest_instant_by_frame()` helper rather than `extract_quarterly_duration_kpi()` — no Q4 derivation needed. `plot_assets.py` mirrors `plot_bvps.py`'s single-hue line-chart style rather than a bar chart.
- **Total Liabilities pairs with Total Assets to reveal a leverage trend BVPS alone doesn't show as starkly:** both are instant measures extracted the same way. From CY2019Q4 to CY2026Q1, total assets roughly doubled ($18.0B → $26.8B) but implied equity (Assets − Liabilities) *shrank* in dollar terms ($1.83B → $0.96B) as the liabilities/assets ratio climbed from 89.8% to 96.4% — the balance sheet grew mostly on borrowed money, corroborating BVPS's decline from the balance-sheet side rather than the per-share side.
- **Debt-to-equity is purely derived, no new API data:** computed as Total Liabilities / Stockholders' Equity by reusing `equity_by_frame` (already built in the BVPS section) and `liabilities_by_frame` — no new SEC concept, no extra API call. Uses total GAAP equity (not common-only, unlike BVPS) since that's the conventional denominator for this ratio. This is the sharpest trend of any KPI so far: the ratio held in a roughly 3–11x band from 2009 through 2023 (aside from a 16x COVID spike in CY2020Q1), then broke out — climbing from 12.5x (CY2024Q2) to 27.0x (CY2026Q1) in just six quarters, nearly double its prior all-time high.

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

`rwt_quarterly_dividends.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q1`) |
| `dividend_per_share` | Dividends declared per common share, in USD |
| `filed` | Date the source filing was submitted to SEC |
| `form` | Form type (`10-Q` or `10-K`) |

`rwt_quarterly_dividends_complete.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q4`) |
| `dividend_per_share` | Dividend per common share in USD (reported or derived) |
| `source` | `reported` (direct from an SEC frame) or `derived (Annual - Q1 - Q2 - Q3)` |

`rwt_quarterly_nii.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q1`) |
| `net_interest_income` | Net interest income in USD (interest income minus interest expense) |
| `filed` | Date the source filing was submitted to SEC |
| `form` | Form type (`10-Q` or `10-K`) |

`rwt_quarterly_nii_complete.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q4`) |
| `net_interest_income` | Net interest income in USD (reported or derived) |
| `source` | `reported` (direct from an SEC frame) or `derived (Annual - Q1 - Q2 - Q3)` |

`rwt_quarterly_net_income.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q1`) |
| `net_income` | Bottom-line net income in USD |
| `filed` | Date the source filing was submitted to SEC |
| `form` | Form type (`10-Q` or `10-K`) |

`rwt_quarterly_net_income_complete.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q4`) |
| `net_income` | Net income in USD (reported or derived) |
| `source` | `reported` (direct from an SEC frame) or `derived (Annual - Q1 - Q2 - Q3)` |

`rwt_quarterly_assets.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q4`) |
| `total_assets` | Total assets in USD, as of quarter-end |
| `filed` | Date the source filing was submitted to SEC |
| `form` | Form type (`10-Q` or `10-K`) |

`rwt_quarterly_liabilities.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q4`) |
| `total_liabilities` | Total liabilities in USD, as of quarter-end |
| `filed` | Date the source filing was submitted to SEC |
| `form` | Form type (`10-Q` or `10-K`) |

`rwt_quarterly_debt_to_equity.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q4`) |
| `debt_to_equity` | Total Liabilities / Stockholders' Equity, rounded to 2dp |
| `total_liabilities` | Total liabilities in USD, as of quarter-end |
| `stockholders_equity` | Total stockholders' equity in USD, as of quarter-end |
| `filed` | Date the source filing was submitted to SEC |
| `form` | Form type (`10-Q` or `10-K`) |

## Next steps (not yet built)

- Extract additional KPIs beyond EPS, book value, dividends, net interest income, net income, total assets, total liabilities, and debt-to-equity
- Filter to a specific date range
- Interactive UI (e.g. Streamlit) if static charts stop being enough
