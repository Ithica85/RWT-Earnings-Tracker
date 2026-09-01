"""Artboards 4-6: index, comparison, phone."""
import sys; sys.path.insert(0, "/Users/danielmcdermott/Documents/Projects/RWT/design")
import _shared as S
from _css import BASE
from build_redesign import DOC, EXTRA, doc

idx = S.index()
comps = {c["ticker"]: S.company(c["ticker"].lower()) for c in idx}
rec = S.recourse()
rec_series = [{"quarter": r["quarter"], "value": float(r["recourse_leverage"])} for r in rec]

# --------------------------------------------------------------------- index

EX2 = EXTRA + """
  .co-grid { display:grid; gap:1px; background:var(--rule); border:1px solid var(--rule);
             grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); }
  .co { background:var(--paper); padding:22px 24px; display:flex; flex-direction:column;
        gap:14px; text-decoration:none; }
  .co:hover { background:var(--paper-2); }
  .co-top { display:flex; align-items:baseline; gap:12px; }
  .co-tk { font-family:var(--mono); font-size:22px; font-weight:600; letter-spacing:-0.01em; }
  .co-nm { font-size:14px; color:var(--ink-2); flex:1; }
  .co-tier { font-family:var(--mono); font-size:11px; letter-spacing:0.12em;
             text-transform:uppercase; padding:4px 9px; border:1px solid currentColor;
             border-radius:2px; font-weight:600; white-space:nowrap; }
  .co-mid { display:flex; align-items:flex-end; gap:16px; justify-content:space-between; }
  .co-fig { display:flex; flex-direction:column; gap:2px; }
  .co-fig .v { font-family:var(--mono); font-variant-numeric:tabular-nums;
               font-size:21px; font-weight:600; }
  .co-fig .k { font-family:var(--mono); font-size:9.5px; letter-spacing:0.11em;
               text-transform:uppercase; color:var(--ink-3); }
  .co-note { font-size:13.5px; color:var(--ink-2); border-top:1px solid var(--rule);
             padding-top:11px; margin:0; }
  .co-note.gold { color:var(--gold); }
  .cmp-cta { display:flex; align-items:center; gap:12px; border:1px solid var(--rule-strong);
             padding:14px 18px; font-size:15px; color:var(--ink-2); }
  .cmp-cta .k { font-family:var(--mono); font-size:10px; letter-spacing:0.14em;
                text-transform:uppercase; color:var(--green); white-space:nowrap; }
"""

cards = []
for c in idx:
    t = c["ticker"]; d = comps[t]
    de = d["kpis"].get("debt_to_equity", {})
    curated = c["tier"] == "curated"
    if curated:
        fig, key, spark = "4.84×", "Recourse leverage", S.sparkline(rec_series, "var(--green)", w=150)
        note = ('<p class="co-note">Gross reads %s. Two figures here carry a correction '
                'because they mislead alone.</p>' % S.fmt(de.get("latest_value"), "multiple"))
    else:
        fig, key = S.fmt(de.get("latest_value"), "multiple"), "Debt-to-equity (gross)"
        spark = S.sparkline(de.get("series", []), "var(--gold)", w=150)
        note = ('<p class="co-note gold">Uncorrected. Nobody has read these filings &mdash; '
                'gross leverage is the figure most likely to be wrong.</p>')
    cards.append(
        '<a class="co" href="#"><div class="co-top"><span class="co-tk">%s</span>'
        '<span class="co-nm">%s</span>'
        '<span class="co-tier tier-%s">%s</span></div>'
        '<div class="co-mid"><div class="co-fig"><span class="v">%s</span>'
        '<span class="k">%s</span></div>%s</div>%s</a>'
        % (t, c["name"].title() if c["name"].isupper() else c["name"], c["tier"],
           c["tier"], fig, key, spark, note))

curated_n = sum(1 for c in idx if c["tier"] == "curated")

INDEX = """
<div class="wrap">
  <div class="board-tag fix">Proposed &middot; index</div>
  <header class="masthead">
    <div class="eyebrow">Independent analysis &middot; Public SEC filings</div>
    <h1>Can this employer afford you?</h1>
    <p class="standfirst">
      Glassdoor tells you what people say about working somewhere. This reads the
      company&rsquo;s own filings and tells you whether it can pay for them &mdash;
      including the figures that are misleading until someone reads the footnotes.
    </p>
  </header>
  <section>
    <div class="sec-head">
      <h2>Companies</h2>
      <span class="note">__CUR__ curated &middot; __GEN__ uncorrected</span>
    </div>
    <div class="co-grid">__CARDS__</div>
    <div class="cmp-cta" style="margin-top:20px">
      <span class="k">Compare &rarr;</span>
      <span>Put any two side by side &mdash; with the tier carried into every column, so a
      checked figure is never silently ranked against an unchecked one.</span>
    </div>
  </section>
  <section>
    <div class="sec-head"><h2>What the two tiers mean</h2></div>
    <div class="tier-banner" style="margin-bottom:14px">
      <span class="lede">Curated</span>
      <p class="body">Someone read the filings. Concept choices are checked, series that
      cross a renaming or a restatement are verified against overlapping periods, and the
      figures that mislead carry a correction.</p>
    </div>
    <div class="tier-banner generic">
      <span class="lede">Uncorrected</span>
      <p class="body">The obvious concepts, pulled automatically, with nobody having looked.
      A starting point, not an answer. On the one company that has been curated, the
      automatic reading of leverage was wrong by roughly six times &mdash; 29.86× against
      4.84×. Assume the same error is present here and unfound.</p>
    </div>
  </section>
  <footer>
    Built from SEC EDGAR: the CompanyFacts API, filing instance documents, and 8-K item
    codes. Independent analysis, not affiliated with or endorsed by any company covered.
    Not investment advice. Figures are as reported and may be restated in later filings.
  </footer>
</div>
"""
open("Index.dc.html", "w").write(doc(EX2, INDEX
    .replace("__CARDS__", "".join(cards)).replace("__CUR__", str(curated_n))
    .replace("__GEN__", str(len(idx) - curated_n))))

# ------------------------------------------------------------------- compare

METRICS = [("debt_to_equity", "Debt-to-equity (gross)", "multiple"),
           ("stockholders_equity", "Stockholders' equity", "usd"),
           ("total_assets", "Total assets", "usd"),
           ("total_liabilities", "Total liabilities", "usd"),
           ("net_income", "Net income", "usd"),
           ("eps", "Diluted EPS", "usd_per_share"),
           ("net_interest_income", "Net interest income", "usd")]

order = ["RWT", "NLY", "AGNC", "PMT", "MFA"]
head = "".join(
    '<th>%s<span class="cmp-tier tier-%s">%s</span></th>'
    % (t, comps[t]["tier"], "curated" if comps[t]["tier"] == "curated" else "uncorrected")
    for t in order)

body_rows = []
for key, label, unit in METRICS:
    cells = []
    for t in order:
        k = comps[t]["kpis"].get(key)
        if not k or not k.get("available", True):
            cells.append('<td class="num muted">—</td>'); continue
        v = k.get("latest_value")
        cls = "neg" if (v or 0) < 0 else ""
        extra = ""
        if key == "debt_to_equity":
            extra = ('<span class="qual" style="color:var(--green)">4.84× recourse</span>'
                     if t == "RWT" else '<span class="qual">unchecked</span>')
        cells.append('<td class="num now %s">%s%s</td>' % (cls, S.fmt(v, unit), extra))
    body_rows.append('<tr><td class="kpi-name">%s</td>%s</tr>' % (label, "".join(cells)))

COMPARE = """
<div class="wrap">
  <div class="board-tag fix">Proposed &middot; comparison (new)</div>
  <header class="masthead">
    <div class="eyebrow">Independent analysis &middot; 5 companies &middot; CY2026Q2</div>
    <h1>Mortgage REITs, side by side</h1>
  </header>

  <div class="tier-banner generic">
    <span class="lede">Read first</span>
    <p class="body">Only RWT has been checked against its filings. On the leverage row this
    matters more than anywhere: RWT&rsquo;s 29.86× is gross, and its corrected figure is
    <b style="color:var(--green)">4.84×</b> &mdash; lower than every peer shown. The other
    four have had no such correction applied, so their figures carry the same error
    unfound. <b>This table is not a ranking</b>, and nothing here sorts.</p>
  </div>

  <section>
    <div class="sec-head">
      <h2>Latest reported quarter</h2>
      <span class="note">figures as filed</span>
    </div>
    <div class="scroller">
      <table>
        <thead><tr><th class="left">Metric</th>__HEAD__</tr></thead>
        <tbody>__ROWS__</tbody>
      </table>
    </div>
  </section>

  <footer>
    Built from SEC EDGAR. Independent analysis, not affiliated with or endorsed by any
    company covered. Not investment advice. Figures are as reported and may be restated.
  </footer>
</div>
"""
open("Compare.dc.html", "w").write(doc(EX2, COMPARE
    .replace("__HEAD__", head).replace("__ROWS__", "".join(body_rows))))

# -------------------------------------------------------------------- mobile

EX3 = EX2 + """
  .m-wrap { max-width:390px; margin:0 auto; padding:22px 18px 40px;
            display:flex; flex-direction:column; gap:30px; }
  .m-wrap h1 { font-size:31px; }
  .m-card { border:1px solid var(--rule); padding:14px 15px; display:flex;
            flex-direction:column; gap:9px; }
  .m-top { display:flex; align-items:baseline; justify-content:space-between; gap:10px; }
  .m-lab { font-size:14.5px; font-weight:600; }
  .m-val { font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:17px;
           font-weight:600; white-space:nowrap; }
  .m-bot { display:flex; align-items:center; justify-content:space-between; gap:10px; }
  .m-meta { font-family:var(--mono); font-size:10.5px; color:var(--ink-3); }
"""

mk = comps["RWT"]["kpis"]
cards_m = []
for key, label, unit in [("stockholders_equity", "Stockholders' equity", "usd"),
                         ("net_income", "Net income", "usd"),
                         ("eps", "Diluted EPS", "usd_per_share"),
                         ("dividends_per_share", "Dividend / share", "usd_per_share")]:
    k = mk[key]; v = k.get("latest_value")
    cards_m.append(
        '<div class="m-card"><div class="m-top"><span class="m-lab">%s</span>'
        '<span class="m-val %s">%s</span></div>'
        '<div class="m-bot">%s<span class="m-meta">%s &middot; %dq</span></div></div>'
        % (label, "neg" if (v or 0) < 0 else "", S.fmt(v, unit),
           S.sparkline(k["series"], "var(--red)" if (v or 0) < 0 else "var(--ink-2)",
                       w=120, h=26, zero=key in ("eps", "net_income")),
           S.fmt_change(S.qoq(k)), k.get("quarters", 0)))

MOBILE = """
<div class="m-wrap">
  <div class="board-tag fix">Proposed &middot; 390px</div>
  <header class="masthead" style="gap:12px;padding-bottom:16px">
    <div class="eyebrow">&larr; All &middot; CIK 0000930236</div>
    <h1>Redwood Trust</h1>
  </header>

  <div class="correct" style="border:1px solid var(--gold)">
    <span class="kpi">Debt-to-equity</span>
    <div class="pair">
      <span class="filed" style="font-size:16px">29.86×</span>
      <span class="arrow">&rarr;</span>
      <span class="true" style="font-size:27px">4.84×</span>
    </div>
    <p class="why" style="font-size:13.5px">GAAP consolidates securitisation entities whose
    creditors have no claim on Redwood. Recourse leverage counts only what the parent can be
    pursued for &mdash; though it has still nearly doubled since 2024.</p>
  </div>

  <section>
    <div class="sec-head" style="margin-bottom:14px">
      <h2 style="font-size:20px">Financial position</h2>
    </div>
    <div style="display:flex;flex-direction:column;gap:9px">__CARDS__</div>
  </section>

  <section>
    <div class="sec-head" style="margin-bottom:14px">
      <h2 style="font-size:20px">Restructuring</h2>
    </div>
    <div class="quiet" style="font-size:14px">
      <strong>No item 2.05 since 2024.</strong> No exit or disposal plan has been disclosed.
      That is not the same as no job cuts.
    </div>
  </section>

  <footer style="font-size:12.5px">
    SEC EDGAR. Independent analysis, not affiliated with Redwood Trust. Not investment advice.
  </footer>
</div>
"""
open("Mobile.dc.html", "w").write(doc(EX3, MOBILE.replace("__CARDS__", "".join(cards_m))))
print("wrote Index.dc.html, Compare.dc.html, Mobile.dc.html")
