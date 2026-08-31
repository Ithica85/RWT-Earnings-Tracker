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
| `get_company_facts.py` | Main script — single SEC API fetch, extracts EPS, book value per share, dividends per share, net interest income, net income, total assets, total liabilities, debt-to-equity ratio, and credit loss allowance (deriving missing Q4 values via a shared helper for the four duration-measure KPIs), exports CSVs |
| `get_operating_expenses.py` | Builds the operating expenses series by splicing two sources — the tagged `OperatingExpenses` total (API, through CY2024Q2) and the four expense components summed from filing instances (CY2024Q3 onward). Verifies the two agree on overlapping periods before splicing, and repairs sign errors in the SEC data |
| `plot_interest_expense.py` | Reads `rwt_quarterly_interest_expense_complete.csv` and renders a bar chart to `rwt_interest_expense_chart.png` (no API call) |
| `plot_operating_expenses.py` | Reads `rwt_quarterly_operating_expenses.csv` and renders a bar chart to `rwt_operating_expenses_chart.png` (no API call) |
| `get_recourse_leverage.py` | Builds the recourse leverage ratio — the honest companion to gross debt-to-equity. Combines the secured recourse debt figure (MD&A narrative, regex-extracted) with corporate debt (XBRL, `CorporateDebtSecuritiesMember`), divided by stockholders' equity |
| `plot_recourse_leverage.py` | Reads `rwt_quarterly_recourse_leverage.csv` and renders gross vs. recourse leverage as two lines with the non-recourse gap shaded, to `rwt_recourse_leverage_chart.png` (no API call) |
| `get_segment_facts.py` | **Per-segment** extraction — a different pipeline to `get_company_facts.py`, because CompanyFacts returns consolidated figures only. Discovers every 10-Q/10-K, downloads and caches each filing's XBRL instance document, and reads dimensional facts tagged against `us-gaap:StatementBusinessSegmentsAxis`. Exports one long CSV plus two chart-ready wide CSVs |
| `plot_eps.py` | Reads `rwt_quarterly_eps_complete.csv` and renders a bar chart to `rwt_eps_chart.png` (no API call) |
| `plot_bvps.py` | Reads `rwt_quarterly_bvps.csv` and renders a line chart to `rwt_bvps_chart.png` (no API call) |
| `plot_dividends.py` | Reads `rwt_quarterly_dividends_complete.csv` and renders a bar chart to `rwt_dividends_chart.png` (no API call) |
| `plot_nii.py` | Reads `rwt_quarterly_nii_complete.csv` and renders a bar chart to `rwt_nii_chart.png` (no API call) |
| `plot_net_income.py` | Reads `rwt_quarterly_net_income_complete.csv` and renders a bar chart to `rwt_net_income_chart.png` (no API call) |
| `plot_assets.py` | Reads `rwt_quarterly_assets.csv` and renders a line chart to `rwt_assets_chart.png` (no API call) |
| `plot_liabilities.py` | Reads `rwt_quarterly_liabilities.csv` and renders a line chart to `rwt_liabilities_chart.png` (no API call) |
| `plot_debt_to_equity.py` | Reads `rwt_quarterly_debt_to_equity.csv` and renders a line chart to `rwt_debt_to_equity_chart.png` (no API call) |
| `plot_leverage_dashboard.py` | Reads `rwt_quarterly_assets.csv`, `rwt_quarterly_liabilities.csv`, and `rwt_quarterly_debt_to_equity.csv` and renders a two-panel combined chart to `rwt_leverage_dashboard.png` (no API call) |
| `plot_credit_loss_allowance.py` | Reads `rwt_quarterly_credit_loss_allowance.csv` and renders a line chart to `rwt_credit_loss_allowance_chart.png` (no API call) |
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
| `rwt_quarterly_credit_loss_allowance.csv` | One row per quarter of the credit loss allowance on available-for-sale debt securities, a balance-sheet "instant" measure (tagged every quarter from CY2019Q4 onward, no derivation needed) |
| `rwt_quarterly_interest_expense.csv` | One row per reported quarter of gross interest expense (the cost side of net interest income) |
| `rwt_quarterly_interest_expense_complete.csv` | Same plus derived Q4, with a `source` column. 68 quarters, CY2009Q2 → CY2026Q2 |
| `rwt_quarterly_operating_expenses.csv` | One row per quarter of total operating expenses, 67 quarters CY2009Q2 → CY2026Q2, with a `source` column distinguishing four provenances |
| `rwt_interest_expense_chart.png` | Output of `plot_interest_expense.py` |
| `rwt_operating_expenses_chart.png` | Output of `plot_operating_expenses.py` |
| `rwt_quarterly_recourse_leverage.csv` | One row per quarter of recourse leverage alongside gross debt-to-equity, CY2024Q2 onward (9 quarters — see the disclosure-window note in design decisions) |
| `rwt_recourse_leverage_chart.png` | Output of `plot_recourse_leverage.py` — gross vs. recourse leverage with the non-recourse band shaded |
| `rwt_segment_quarterly.csv` | Long/tidy format — one row per segment × quarter × line item, across **all** segment structures, with full provenance (`filed`, `segment_structure`) so a reader can tell which rows are comparable |
| `rwt_segment_contribution.csv` | Wide format — segment net income (contribution), one row per quarter, one column per segment. Restricted to the current 6-segment structure |
| `rwt_segment_assets.csv` | Wide format — assets allocated per segment, same shape and same restriction as above |
| `sec_cache/` | Downloaded XBRL instance documents, ~5 MB each (gitignored — re-downloadable at any time) |
| `rwt_eps_chart.png` | Output of `plot_eps.py` — quarterly EPS bar chart |
| `rwt_bvps_chart.png` | Output of `plot_bvps.py` — quarterly BVPS line chart |
| `rwt_dividends_chart.png` | Output of `plot_dividends.py` — quarterly dividends-per-share bar chart |
| `rwt_nii_chart.png` | Output of `plot_nii.py` — quarterly net interest income bar chart |
| `rwt_net_income_chart.png` | Output of `plot_net_income.py` — quarterly net income bar chart |
| `rwt_assets_chart.png` | Output of `plot_assets.py` — quarterly total assets line chart |
| `rwt_liabilities_chart.png` | Output of `plot_liabilities.py` — quarterly total liabilities line chart |
| `rwt_debt_to_equity_chart.png` | Output of `plot_debt_to_equity.py` — quarterly debt-to-equity ratio line chart |
| `rwt_leverage_dashboard.png` | Output of `plot_leverage_dashboard.py` — combined Assets/Liabilities + Debt-to-Equity dashboard |
| `rwt_credit_loss_allowance_chart.png` | Output of `plot_credit_loss_allowance.py` — quarterly credit loss allowance line chart |

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
16. Extracts `DebtSecuritiesAvailableForSaleAllowanceForCreditLoss` (credit loss allowance on AFS debt securities — the current, CECL-era replacement for the retired `ProvisionForLoanLeaseAndOtherLosses` concept, which stopped being tagged after 2018) and exports to `rwt_quarterly_credit_loss_allowance.csv`

## What get_segment_facts.py does

A separate pipeline from `get_company_facts.py`. The CompanyFacts API returns **consolidated** figures only — one number per concept per period for the whole company. Segment breakdowns are *dimensional* facts that live in each filing's own XBRL instance document, so they need a different approach.

1. Calls `data.sec.gov/submissions/CIK0000930236.json` to discover every 10-Q and 10-K filed on or after `EARLIEST_FILING` (2025-01-01 — before that the segment structure is unrecognisably different)
2. Downloads each filing's XBRL instance (`rwt-YYYYMMDD_htm.xml`, ~5 MB) into `sec_cache/`, **skipping anything already cached** — only new filings cost a request
3. Parses XBRL *contexts* into `(segment, period)` pairs. A context is XBRL's way of saying "this number is about this entity, over this period, sliced these ways". Contexts carrying dimensions beyond segment + consolidation are rejected — those are sub-breakdowns (by range, by counterparty) that must not be mixed into clean segment totals
4. Converts periods to calendar frames: ~90-day durations become `CY2026Q2`, ~365-day become `CY2026`, instants become `CY2026Q2I`. Six- and nine-month year-to-date periods are skipped
5. Extracts 22 line items per segment — a full P&L (interest income/expense, mortgage banking activities, fair value changes, HEI, servicing, fees, G&A, portfolio management, loan acquisition, tax, net income) plus `Assets`
6. Dedupes by latest filing, same convention as `get_company_facts.py`
7. Derives Q4 as `Annual − Q1 − Q2 − Q3`, **but only when all four inputs come from filings reporting the same set of segments** (see design decisions below)
8. Exports `rwt_segment_quarterly.csv` (long, all structures, with provenance) plus `rwt_segment_contribution.csv` and `rwt_segment_assets.csv` (wide, current structure only)

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

## What plot_leverage_dashboard.py does

Reads `rwt_quarterly_assets.csv`, `rwt_quarterly_liabilities.csv`, and `rwt_quarterly_debt_to_equity.csv` (does not call the SEC API) and renders a combined two-panel chart to `rwt_leverage_dashboard.png`. Built with the dataviz skill's procedure:

1. **Two stacked panels sharing one x-axis, not a dual-axis chart** — Assets/Liabilities ($B) and the Debt-to-Equity ratio (a dimensionless multiple) are different scales, so per the skill's non-negotiable ("never two y-scales on one axis"), they get small multiples instead
2. **Top panel:** Total Assets and Total Liabilities as two categorical-hued lines (blue `#2a78d6`, orange `#eb6834` — validated for CVD separation via the skill's `validate_palette.js`), with the gap between them shaded in muted gray to visualize implied equity (Assets − Liabilities) as a derived area, not a third competing series
3. **Bottom panel:** Debt-to-equity ratio, single-hue blue (consistent with `plot_debt_to_equity.py` since it's alone in its own panel)
4. A legend on the top panel (required for 2 series); both panels direct-label only their endpoint values
5. Debt-to-equity has a few quarters (2013–2015) where `StockholdersEquity` wasn't framed, unlike Assets/Liabilities which have full coverage — those gaps are plotted as `NaN` on a shared numeric x-axis (indexed to Assets' quarters) so the line breaks visibly at the gap instead of connecting straight across it or drifting out of alignment with the other two series

## What plot_credit_loss_allowance.py does

Reads `rwt_quarterly_credit_loss_allowance.csv` (does not call the SEC API) and renders a line chart to `rwt_credit_loss_allowance_chart.png`:

1. Same single-hue line style as `plot_assets.py` / `plot_liabilities.py` / `plot_bvps.py`
2. Direct-labels only the most recent quarter's value
3. Values are divided by 1,000,000 before plotting so the y-axis reads in $M — this KPI is two to three orders of magnitude smaller than Assets/Liabilities, so it gets its own scale rather than $B

## How to run

```
python3 get_company_facts.py
python3 get_segment_facts.py
python3 get_operating_expenses.py
python3 get_recourse_leverage.py
python3 plot_eps.py
python3 plot_bvps.py
python3 plot_dividends.py
python3 plot_nii.py
python3 plot_net_income.py
python3 plot_assets.py
python3 plot_liabilities.py
python3 plot_debt_to_equity.py
python3 plot_leverage_dashboard.py
python3 plot_credit_loss_allowance.py
python3 plot_recourse_leverage.py
python3 plot_interest_expense.py
python3 plot_operating_expenses.py
```

Requires the `requests`, `matplotlib` and `lxml` libraries. Install them with:

```
pip3 install requests matplotlib lxml
```

`get_segment_facts.py` downloads ~37 MB of XBRL instance documents on its first run and caches them in `sec_cache/`. Later runs only fetch filings that are new.

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
- **Total Liabilities pairs with Total Assets to reveal a leverage trend BVPS alone doesn't show as starkly:** both are instant measures extracted the same way. From CY2019Q4 to CY2026Q1, total assets grew 49% ($18.0B → $26.8B, roughly doubling only if measured from the CY2023Q2 trough of $12.8B instead) but implied equity (Assets − Liabilities) *shrank* in dollar terms ($1.83B → $0.96B) as the liabilities/assets ratio climbed from 89.8% to 96.4% — the balance sheet grew mostly on borrowed money, corroborating BVPS's decline from the balance-sheet side rather than the per-share side.
- **Debt-to-equity is purely derived, no new API data:** computed as Total Liabilities / Stockholders' Equity by reusing `equity_by_frame` (already built in the BVPS section) and `liabilities_by_frame` — no new SEC concept, no extra API call. Uses total GAAP equity (not common-only, unlike BVPS) since that's the conventional denominator for this ratio. This is the sharpest trend of any KPI so far: the ratio held in a roughly 3–11x band from 2009 through 2023 (aside from a 16x COVID spike in CY2020Q1), then broke out — climbing from 12.5x (CY2024Q2) to 27.0x (CY2026Q1) in just six quarters, nearly double its prior all-time high.
- **Interest expense needed a concept-rename splice, and the rename was verified before splicing:** `InterestExpense` runs CY2009Q2 → CY2024Q2 then stops dead; `InterestExpenseOperating` starts CY2023Q2 and continues. They are the same measure — **all four overlapping quarters agree to the dollar** (CY2023Q2 152,885,000 · CY2023Q3 156,723,000 · CY2024Q1 180,530,000 · CY2024Q2 200,124,000) — so `extract_quarterly_duration_kpi()` gained a `successor_concepts` parameter that pools their records before deduping. Only ever pass a successor after checking the overlap agrees; if the two disagree they measure different things and splicing invents a step.
- **Operating expenses cannot come from the API at all for recent quarters:** the `OperatingExpenses` total stops at CY2024Q2 with no successor concept — filings now tag only the four components, and two of them (`PortfolioManagementCosts`, `LoanAcquisitionCosts`) are Redwood's own custom tags. CompanyFacts serves only standard taxonomies (`dei`, `invest`, `srt`, `us-gaap`, `ffd`), so the recent total must be summed from filing instances. `get_operating_expenses.py` splices API totals (through CY2024Q2) with component sums (CY2024Q3 onward) and **fails loudly if any overlapping period disagrees** — all 4 currently agree to the dollar, and the CY2026Q1/Q2 component sums ($71.9M, $56.0M) match the "$72 million"/"$56 million" stated in that quarter's MD&A.
- **The SEC data contains sign errors, and they need different treatment depending on whether the intended value is provable:** RWT's 10-K filed 2015-02-25 tagged all four quarters of 2013 as *negative* operating expenses. `repair_negatives()` distinguishes two cases. **Provable** — every quarter of the year is negative and they sum to exactly minus the annual figure (CY2013: −86,607,000 vs annual +86,607,000), so magnitudes are right and only the sign is inverted; signs are flipped and rows marked `sign corrected`. **Unprovable** — an isolated negative like CY2009Q3, where the year's other quarters are positive and the sum test cannot run; the quarter is dropped rather than guessed at. Never take absolute values indiscriminately, which would hide genuine problems.
- **CY2020Q1 operating expenses of $124.1M is real, not an artifact** — roughly 2.5× neighbouring quarters ($49.4M and $35.2M), and it is the COVID quarter that also produced the −$943M net loss and −8.28 EPS. Left unclipped; the bar is legible and does not flatten the rest of the series.
- **Recourse leverage is the honest version of debt-to-equity, and it needs two sources:** gross debt-to-equity hit 29.9x in CY2026Q2, which read literally implies distress. Most of those liabilities belong to consolidated securitisation entities whose creditors have no claim on Redwood Trust, Inc. The recourse figure comes from `secured recourse debt` (stated only in the MD&A narrative, extracted by regex — **not XBRL-tagged anywhere**) plus corporate debt (XBRL `DebtInstrumentFaceAmount` under `DebtInstrumentAxis = CorporateDebtSecuritiesMember`, which avoids double-counting instruments that are also tagged under their own axis). Result: **4.84x, not 29.86x.**
- **Two independent paths reconcile the recourse figure:** secured recourse 3.620B + corporate 0.902B + secured non-recourse 0.450B = 4.972B, against an undimensioned total debt face amount of 4.978B tagged in the same filing. Re-run this check if the extraction changes.
- **The recourse series starts at CY2024Q2 because of a disclosure change, not a data gap.** Before the 2024-08-07 filing, corporate debt is not tagged under `CorporateDebtSecuritiesMember` — it appears only as fair-value disclosures (`ConvertibleDebtFairValueDisclosures` and friends), a different measurement basis to the face amounts used later. Separately, the three 2023 10-Qs say "recourse debt" rather than "**secured** recourse debt", and that unqualified figure appears to already include corporate debt, so adding corporate debt to it would double-count. Splicing either would produce a step reflecting accounting presentation rather than borrowing. `get_recourse_leverage.py` never treats a missing corporate figure as zero — that would understate recourse debt by ~$0.9B and flatter the ratio.
- **The two leverage lines legitimately share one y-axis** — both are dimensionless multiples of equity, so this is not the dual-axis anti-pattern; the whole point is that they are directly comparable and the gap is enormous. The shaded band between them is consolidated non-recourse debt. No texture on the band: it is a derived area rather than a third series, and the two real series carry identity through position, a CVD-validated hue pair (ΔE 24.7 protan), the legend and end labels.
- **Segment data needs a whole separate pipeline, not another KPI:** CompanyFacts has no dimensional data at all, so `get_segment_facts.py` downloads and parses filing instance documents instead. Instances are ~5 MB each and cached to `sec_cache/`; the rendered `R54.htm` report is 26× smaller (211 KB) but its R-number shifts between filings and its row/column mapping is positional, so the instance was chosen for stability over bandwidth.
- **Redwood has redrawn its segments three times in four years, and this is the dominant constraint on segment analysis:** 2022–2023 reported Business Purpose Lending / Residential Lending / Third-Party Residential Investments; 2024 reported Residential Consumer Mortgage Banking / Residential Investor Lending / Residential Lending / Third-Party Residential Investments; 2025 reported CoreVest / Sequoia / Redwood Investments / Legacy Investments; 2026 added Aspire. **There is no long segment history to be had** — unlike the consolidated KPIs, which go back to 2009.
- **Q4 derivation must not cross a segment restructure.** The arithmetic is the same as `extract_quarterly_duration_kpi()`, but subtracting quarters reported under one structure from an annual reported under another produces a plausible-looking wrong number. Concretely: the FY2025 annual predates the Aspire segment while Q1/Q2 2025 were later restated to include it, so a naive subtraction buries Aspire's whole result inside another segment's Q4 — the error was exactly Aspire's contribution. `derive_q4()` now requires all four inputs to share a segment structure and skips the quarter otherwise. This currently means **no derived segment Q4 at all** for 2024 or 2025.
- **Restatement across structures is material for income, cosmetic for assets** (measured empirically by comparing CY2025Q2 as reported in the 5-segment 2025-08-08 filing against the 6-segment 2026-08-05 filing). *Assets:* Aspire's $137.8M was carved out of Sequoia exactly — every other segment identical to the dollar. *Income statement:* every segment moved, driven by a net-interest-income reallocation (Corporate +$16.6M, Legacy −$6.0M, Redwood Investments −$4.6M, Sequoia −$3.8M, CoreVest −$0.9M). So older segment income figures are **not** comparable to current ones, which is why the wide CSVs are restricted to the current structure. That currently yields **4 quarters** (CY2025Q1–Q2, CY2026Q1–Q2), growing by one per filing.
- **Segment extraction validates cleanly against two independent sources:** segment contributions sum to consolidated `NetIncomeLoss` to the dollar ($0 difference) for all seven reported quarters, and CoreVest's CY2026Q1/Q2 values (−$3.29M, +$1.26M) match the Q2 2026 MD&A narrative ("segment net loss of $3 million... segment income of $1 million") exactly.
- **"Loan loss provisions" needed a concept swap:** the originally-planned `ProvisionForLoanLeaseAndOtherLosses` stopped being tagged after 2018 (retired when the CECL accounting standard changed credit-loss reporting starting 2020), so building on it would produce a chart with no current data. `DebtSecuritiesAvailableForSaleAllowanceForCreditLoss` is the modern equivalent — an instant (balance) measure with full coverage from CY2019Q4 onward, reusing `latest_instant_by_frame()`. Small dollar magnitude (under $5M throughout), so it's plotted in $M rather than $B, unlike Assets/Liabilities.

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

`rwt_quarterly_credit_loss_allowance.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2025Q4`) |
| `credit_loss_allowance` | Credit loss allowance on AFS debt securities in USD, as of quarter-end |
| `filed` | Date the source filing was submitted to SEC |
| `form` | Form type (`10-Q` or `10-K`) |

`rwt_quarterly_operating_expenses.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2026Q2`) |
| `operating_expenses` | Total operating expenses in USD |
| `source` | `reported (OperatingExpenses)`, `reported (OperatingExpenses, sign corrected)`, `components (G&A + portfolio + acquisition + other)`, or `derived (Annual - Q1 - Q2 - Q3)` |
| `filed` | Date the source filing was submitted to SEC |
| `form` | Form type (`10-Q` or `10-K`) |

`rwt_segment_quarterly.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2026Q2`) |
| `segment` | `SequoiaMortgageBanking`, `CoreVestMortgageBanking`, `AspireMortgageBanking`, `RedwoodInvestments`, `LegacyInvestments`, or `Corporate` |
| `line_item` | One of the 22 extracted concepts (e.g. `segment_contribution`, `net_interest_income`, `segment_assets`) |
| `value` | Value in USD |
| `source` | `reported` or `derived (Annual - Q1 - Q2 - Q3)` |
| `filed` | Date of the filing this value came from |
| `segment_structure` | Signature of the segment set that filing reported — rows with different signatures are **not** comparable |

`rwt_segment_contribution.csv` / `rwt_segment_assets.csv`:

| Column | Description |
|--------|-------------|
| `quarter` | Calendar period (e.g. `CY2026Q2`) |
| *one column per segment* | Segment net income (contribution) or allocated assets, in USD |

## Next steps (not yet built)

- Extract additional KPIs beyond EPS, book value, dividends, net interest income, net income, total assets, total liabilities, debt-to-equity, and credit loss allowance (the dashboard is a combined view of assets/liabilities/D-to-E, not a new SEC extraction)
- Filter to a specific date range
- Interactive UI (e.g. Streamlit) if static charts stop being enough
