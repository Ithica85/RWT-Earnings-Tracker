# Employer intelligence from SEC filings

## What this is

A public site that reads a company's own SEC filings and reports whether it can
afford its staff — including the figures that mislead until someone reads the
footnotes. Five mortgage REITs are covered today; the engine works for any of
the ~10,400 filers in the SEC ticker map.

Redwood Trust (RWT, CIK 0000930236) is the curated reference implementation and
the origin of the project, which began as a personal KPI tracker for one company.

**Two things are deliberately out of scope and should stay out.**

1. **Review content.** Scraping Glassdoor/Indeed/LinkedIn violates their terms
   and they litigate; user-generated reviews also have a cold-start and
   moderation problem. Dropping them made this a company-intelligence product,
   which is stronger.
2. **Predicting layoffs or re-orgs.** A probability attached to a named real
   employer can move a stock and affect real people's jobs, and is indefensible
   when wrong. What replaced it is a timeline of legally-required disclosures.
   **Never reintroduce a layoff probability.**

## Architecture

Three layers, and the separation is the whole point: generic plumbing,
company-specific truth, and a presentation layer that cannot drop a correction.

| Layer | Path | Responsibility |
|-------|------|----------------|
| Engine | `ingest/edgar/` | Generic, works for any CIK. `client.py` (process-wide rate limiter, `SEC_USER_AGENT` env var, ticker→CIK), `facts.py` (CompanyFacts logic, parameterised on facts rather than a global), `xbrl.py` (filing instance parsing) |
| Judgment | `ingest/profiles/*.yaml` | Per-company. Which concept means what, which splices are safe, which figures mislead. `rwt.yaml` encodes every hard-won correction; `_default.yaml` is the generic fallback |
| Signals | `ingest/signals/eight_k.py` | 8-K item codes from the free submissions feed. Works for all filers with zero per-company config |
| Export | `ingest/export_web.py` | Assembles per-company JSON into `web/data/` |
| Web | `web/` | Next.js static export. All reads go through `web/lib/data.ts` |

**No database, deliberately.** The corpus is ~230 KB for five companies and
changes four times a year, when companies file. Static JSON → static pages. A
database earns its place when arbitrary tickers are generated on demand; because
every read goes through `web/lib/data.ts`, that swap is one module's problem.

### The root-level scripts

The `get_*.py` and `plot_*.py` scripts at the repo root predate the `ingest/`
package. They are **not** legacy — they compute the three measures the
CompanyFacts API cannot produce for Redwood at all, writing CSVs that the
profile loader reads back (see `derived_elsewhere` below), plus the PNG charts
for the published dashboard.

| Script | Produces |
|--------|----------|
| `get_company_facts.py` | The original single-company extraction, incl. `rwt_quarterly_bvps.csv` |
| `get_operating_expenses.py` | `rwt_quarterly_operating_expenses.csv` — API totals spliced with component sums |
| `get_recourse_leverage.py` | `rwt_quarterly_recourse_leverage.csv` — MD&A prose + XBRL corporate debt |
| `get_segment_facts.py` | Per-segment extraction from filing instances (not yet surfaced in the web app) |
| `plot_*.py` | One chart each, read a CSV, call no API |
| `build_dashboard.py` | Inlines the PNGs into `rwt_dashboard.html` (gitignored build product) |
| `design/build_*.py` | Regenerate the design-review artboards from `web/data/*.json` |

## How to run

```bash
pip3 install requests matplotlib lxml pyyaml      # dependencies

python3 -m ingest.export_web                      # regenerate web/data/*.json
python3 tests/check_regression.py                 # ALWAYS after an engine change

cd web && npx next build                          # static export to web/out/
```

`next start` does **not** work with `output: "export"` — serve `web/out/` with any
static server. `get_segment_facts.py` downloads ~37 MB of XBRL instances on first
run and caches them in `sec_cache/`; later runs fetch only new filings.

## The two tiers, and why the badge matters

Every company carries a tier, and it must always be displayed.

- **curated** — someone read the filings. Concept choices are checked, splices
  verified against overlapping periods, misleading figures carry a correction.
- **generic** — the obvious concepts pulled automatically, nobody has looked.

This is not cosmetic. The generic reading of Redwood's leverage is **29.86×**;
the figure the company is actually liable for is **4.84×** — wrong by roughly six
times. The generic tier is also thin (7 KPIs, no segments, no recourse leverage),
so comparing a curated company against a generic one compares unlike things.

## Where per-company judgment lives

`ingest/profiles/rwt.yaml` is the source of truth for Redwood-specific
extraction judgment. Do not duplicate its notes here — they drift. Its blocks:

| Block | Meaning |
|-------|---------|
| `kpis:` | Concepts pulled straight from CompanyFacts. `kind: instant` or `duration`, optional `successors:` for a concept rename |
| `derived_elsewhere:` | Measures CompanyFacts cannot produce at all. Each names its `script`, the `csv` it writes and the `column` to read. The loader reads the series back rather than reimplementing the judgment |
| `caveats:` | Traps. A KPI listed here must never display without its companion — the naive reading is actively misleading, not merely incomplete |
| `known_data_issues:` | Defects in what the SEC serves, and what was done about each |
| `segments:` | The current segment set and why the history is not comparable |

**Caveats are bound to their KPI at the data layer**, in `attachCaveats()` in
`web/lib/data.ts`, not by convention in a component. A figure that misleads on
its own cannot render without its correction even if a future page forgets.

## Rules that generalise

These apply to any company and any KPI. The instances live in the profiles.

- **Dedupe by latest filing.** The SEC stores every version of a reported
  figure; keep the most recently filed value per frame so restatements win.
- **Instant vs duration frames.** Balance-sheet concepts are point-in-time and
  carry frames ending in `I` (`CY2025Q4I`); the SEC tags Q4 directly, so no
  derivation is needed. Income-statement concepts are durations and usually
  have no standalone Q4 frame.
- **Derive Q4 as `Annual − Q1 − Q2 − Q3`**, and tag every derived row so it is
  never confused with a reported one.
- **Never derive Q4 across a segment restructure.** The arithmetic is the same
  but subtracting quarters reported under one structure from an annual reported
  under another produces a plausible, wrong number.
- **Never splice a successor concept without checking the overlap.** If the two
  disagree they measure different things, and splicing invents a step that never
  happened.
- **Never take absolute values to repair sign errors.** Flip signs only where
  the intended value is provable (the year's quarters sum to exactly minus the
  annual figure); drop the quarter where it is not, rather than guessing.
- **Use `record.get("frame")`,** not `record["frame"]` — many records have none.
- **A percentage change across a sign flip, or on a zero base, is misleading
  rather than informative.** Return nothing and render an em dash.
- **Never treat a missing component as zero.** In recourse leverage that would
  understate debt by ~$0.9B and flatter the ratio.

## What has been learned about Redwood

Findings, as distinct from extraction mechanics.

- **Gross leverage is not the honest number.** GAAP consolidates securitisation
  entities whose creditors have no claim on Redwood Trust, Inc. Gross
  debt-to-equity reached 29.86× in CY2026Q2; recourse leverage was **4.84×**.
  The honest caveat on the caveat: recourse leverage has still nearly doubled
  since 2024, and part of that is equity shrinking rather than borrowing growing.
- **The recourse figure reconciles two independent ways:** secured recourse
  3.620B + corporate 0.902B + secured non-recourse 0.450B = 4.972B, against an
  undimensioned total debt face amount of 4.978B tagged in the same filing.
  Re-run this check if the extraction changes.
- **The recourse series starts CY2024Q2 because of a disclosure change, not a
  data gap.** Earlier filings tag corporate debt only as fair-value disclosures,
  a different measurement basis; and the 2023 10-Qs say "recourse debt" rather
  than "*secured* recourse debt", a figure that already includes corporate debt.
  Splicing either would produce a step reflecting presentation, not borrowing.
- **The balance sheet grew mostly on borrowed money.** CY2019Q4 → CY2026Q1,
  total assets grew 49% ($18.0B → $26.8B) while implied equity *shrank* in dollar
  terms ($1.83B → $0.96B), as liabilities/assets climbed from 89.8% to 96.4%.
- **The credit-loss build is one asset, not a portfolio.** Effectively the entire
  $9.9M half-year build is a re-mark of a single retained interest in the Legacy
  Trust, a wind-down vehicle. Ring-fenced and shrinking by design.
- **Segments were redrawn three times in four years**, so there is no long
  segment history — unlike the consolidated KPIs, which reach back to 2009.
  Restatement across structures is material for income (a net-interest-income
  reallocation touching every segment) and cosmetic for assets. Only four
  quarters are currently comparable.
- **The 8-K signal is silent sector-wide.** No item 2.05 since 2024 across any
  of the five companies. Only 5.02s appear, and 5.02 covers both a CFO resigning
  and a routine board election, so it is classified medium, not high. The free
  universal signal is mostly empty; the value is in reading filing text.
- **CY2020Q1 is real, not an artifact.** Operating expenses of $124.1M (~2.5×
  neighbours), a −$943M net loss and −8.28 EPS are all the same COVID quarter.

## Charting conventions

- Sign-carrying series (EPS, net income) get red/green bars; magnitudes (assets,
  BVPS) get a single hue. Derived Q4 bars are hatched.
- Never two y-scales on one axis. Different units get stacked panels sharing an
  x-axis. Two dimensionless multiples (gross vs recourse leverage) legitimately
  share one axis — that is the point of the comparison.
- Direct-label the most recent point only; no legend for a single series.
- Clip an outlier that flattens the rest, and annotate the clipped bar with its
  real value.

## Published surfaces

Both are private Artifacts on claude.ai. Pass the existing URL when updating so
they change in place rather than minting a new one.

| Surface | URL | Built by |
|---------|-----|----------|
| KPI dashboard | `claude.ai/code/artifact/554825df-0449-4932-83a7-6dd1904b4925` | `build_dashboard.py` from `rwt_dashboard_template.html` |
| Design review canvas | `claude.ai/code/artifact/4ce561a0-9403-4ca1-99a1-ca5beb3efd4b` | `design/build_*.py` |

The dashboard's look is SEC-filing vernacular — cover-page masthead, hairline
rules, numbered exhibits, Iowan/Palatino serif with system mono for every figure,
tabular figures throughout. Colours: bone `#F2F3EF`, ink `#191C19`, ledger green
`#2B5D4F`, filing red `#AB3226`, muted gold `#8A7433` for caveats. `web/app/globals.css`
carries the same tokens. A strict CSP blocks external hosts, so everything inlines.

## The safety net

`tests/fixtures/` holds 20 verified CSVs with checksums; `tests/check_regression.py`
does byte comparison **plus** correctness invariants (segment sums reconcile to
consolidated net income, recourse components sum, no negative operating expenses).
Run it after any engine change.

## Record shapes

A CompanyFacts record:

```python
{
  "start": "2025-01-01", "end": "2025-03-31",   # period
  "val": 0.10,                                   # value in the unit
  "accn": "0000930236-26-000020",                # accession number
  "fy": 2026, "fp": "Q1", "form": "10-Q",
  "filed": "2026-05-07",
  "frame": "CY2026Q1"                            # NOT always present
}
```

An exported KPI in `web/data/<ticker>.json`: `label`, `available`, `unit`
(`usd` · `usd_per_share` · `multiple`), `quarters`, `first`, `latest`,
`latest_value`, `note`, and `series` as `[{quarter, value}]`. Caveats are
top-level and bound to their KPI at load time.

## Next steps

1. **The design review's component work** — the corrected-figures band (now
   unblocked, since `recourse_leverage` is a real KPI), the promoted tier
   banner, sparklines and the leverage chart as inline SVG, the comparison
   route, the mobile reflow. See the canvas above.
2. **Deploy** to Vercel.
3. **Phase 2 signals** — WARN notices (biggest and messiest), ATS job boards via
   the public Greenhouse/Lever/Ashby endpoints, editorial notes.
4. **Phase 3** — any-ticker on demand, at which point a database earns its place.
5. **Surface segment data**, which is extracted but not yet exported.
