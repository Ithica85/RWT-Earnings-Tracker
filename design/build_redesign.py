"""Artboards 3-6: the proposed pages, same tokens, different hierarchy."""
import sys; sys.path.insert(0, "/Users/danielmcdermott/Documents/Projects/RWT/design")
import _shared as S
from _css import BASE

DOC = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <style>__CSS__</style>
</helmet>
__BODY__
</x-dc>
</body>
</html>
"""
def doc(extra, body):
    return DOC.replace("__CSS__", BASE + extra).replace("__BODY__", body)

EXTRA = """
  .tier-banner {
    display:flex; gap:14px; align-items:flex-start;
    border-left:3px solid var(--green); background:var(--paper-2);
    padding:14px 18px;
  }
  .tier-banner .lede {
    font-family:var(--mono); font-size:12px; letter-spacing:0.14em;
    text-transform:uppercase; color:var(--green); font-weight:600;
    white-space:nowrap; padding-top:2px;
  }
  .tier-banner .body { font-size:15px; color:var(--ink-2); margin:0; }
  .tier-banner.generic { border-left-color:var(--gold); }
  .tier-banner.generic .lede { color:var(--gold); }

  .correct-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1px;
                  background:var(--rule); border:1px solid var(--rule); }
  .correct { background:var(--gold-wash); padding:20px 22px; display:flex;
             flex-direction:column; gap:10px; }
  .correct .kpi { font-family:var(--mono); font-size:10px; letter-spacing:0.13em;
                  text-transform:uppercase; color:var(--ink-2); }
  .correct .pair { display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; }
  .correct .filed { font-family:var(--mono); font-variant-numeric:tabular-nums;
                    font-size:19px; color:var(--ink-3); text-decoration:line-through;
                    text-decoration-thickness:1px; }
  .correct .arrow { color:var(--ink-3); font-size:14px; }
  .correct .true { font-family:var(--mono); font-variant-numeric:tabular-nums;
                   font-size:31px; font-weight:600; color:var(--green); line-height:1; }
  .correct .true.flag { font-size:19px; color:var(--gold); }
  .correct .why { font-size:14px; color:var(--ink-2); margin:0; }
  .correct .limit { font-size:13px; color:var(--ink-2); border-top:1px solid var(--gold);
                    padding-top:9px; margin:0; }
  .correct .limit b { color:var(--ink); font-weight:600; }

  .lede-figs { display:flex; gap:34px; flex-wrap:wrap; }
  .lede-fig { display:flex; flex-direction:column; gap:3px; }
  .lede-fig .v { font-family:var(--mono); font-variant-numeric:tabular-nums;
                 font-size:25px; font-weight:600; }
  .lede-fig .k { font-family:var(--mono); font-size:10px; letter-spacing:0.12em;
                 text-transform:uppercase; color:var(--ink-3); }

  td.trend { width:150px; padding-top:9px; padding-bottom:9px; }
  .qual { font-family:var(--mono); font-size:10.5px; color:var(--ink-3);
          letter-spacing:0.04em; display:block; }
  .row-flag { font-family:var(--mono); font-size:9.5px; letter-spacing:0.1em;
              text-transform:uppercase; color:var(--gold); border:1px solid var(--gold);
              border-radius:2px; padding:1px 5px; margin-left:8px; white-space:nowrap; }

  .sig-strip { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
  .sig-chip { display:flex; gap:8px; align-items:baseline; border:1px solid var(--rule);
              border-radius:2px; padding:6px 10px; font-family:var(--mono); font-size:11.5px;
              color:var(--ink-2); }
  .sig-chip .d { color:var(--ink-3); font-variant-numeric:tabular-nums; }

  .cmp-tier { font-family:var(--mono); font-size:9px; letter-spacing:0.1em;
              text-transform:uppercase; display:block; margin-top:3px; }
"""

d = S.company("rwt")
K = d["kpis"]
rec = S.recourse()
GREEN, RED, INK3 = "var(--green)", "var(--red)", "var(--ink-3)"

# --- the recourse series the export should be producing (finding 3) ----------
rec_series = [{"quarter": r["quarter"], "value": float(r["recourse_leverage"])} for r in rec]

def qoq_cell(k):
    """QoQ, with a word where a bare percentage on a negative base misleads."""
    s = k.get("series") or []
    ch = S.qoq(k)
    txt = S.fmt_change(ch)
    if len(s) >= 2:
        p, c = s[-2]["value"], s[-1]["value"]
        if p < 0 and c < 0:
            word = "narrower loss" if abs(c) < abs(p) else "wider loss"
            return '%s<span class="qual">%s</span>' % (txt, word)
    return txt

ORDER = [("debt_to_equity", "recourse"), ("debt_to_equity", None), ("stockholders_equity", None),
         ("total_assets", None), ("total_liabilities", None), ("net_income", None),
         ("eps", None), ("net_interest_income", None), ("interest_expense", None),
         ("dividends_per_share", None), ("credit_loss_allowance", None)]

rows = []
for key, variant in ORDER:
    k = K[key]
    if variant == "recourse":
        # Read from the exported KPI now that the loader emits it, rather than
        # hardcoding the figures - a mockup that cannot go stale with the data.
        r = K["recourse_leverage"]
        rows.append(
            '<tr><td class="kpi-name">Leverage &mdash; recourse'
            '<span class="row-flag">corrected</span></td>'
            '<td class="trend">%s</td>'
            '<td class="num now">%s</td>'
            '<td class="num muted">%s<span class="qual">vs CY2026Q1</span></td>'
            '<td class="num muted">%dq from %s</td></tr>'
            % (S.sparkline(r["series"], "var(--green)"),
               S.fmt(r["latest_value"], r["unit"]), S.fmt_change(S.qoq(r)),
               r["quarters"], r["first"]))
        continue
    label = k["label"]
    cav = k.get("caveats", [])
    flag = '<span class="row-flag">see note</span>' if cav else ""
    neg = (k.get("latest_value") or 0) < 0
    colour = "var(--red)" if neg else "var(--ink-2)"
    rows.append(
        '<tr><td class="kpi-name">%s%s</td>'
        '<td class="trend">%s</td>'
        '<td class="num now %s">%s</td>'
        '<td class="num muted">%s</td>'
        '<td class="num muted">%dq from %s</td></tr>'
        % (label, flag, S.sparkline(k["series"], colour, zero=neg or key in ("eps", "net_income")),
           "neg" if neg else "", S.fmt(k.get("latest_value"), k.get("unit")),
           qoq_cell(k), k.get("quarters", 0), k.get("first", "")))

sig_chips = "".join(
    '<span class="sig-chip"><span class="d">%s</span>%s &middot; %s</span>'
    % (s["date"], s["item"], s["meaning"].split("—")[0].strip()[:44]) for s in d["signals"])

MAIN = """
<div class="wrap">
  <div class="board-tag fix">Proposed &middot; company page</div>

  <header class="masthead">
    <div class="eyebrow">&larr; All companies &middot; CIK __CIK__ &middot; through CY2026Q2</div>
    <h1>__NAME__</h1>
    <div class="lede-figs">
      <div class="lede-fig"><span class="v">4.84×</span><span class="k">Recourse leverage</span></div>
      <div class="lede-fig"><span class="v">__EQ__</span><span class="k">Equity</span></div>
      <div class="lede-fig"><span class="v">__DIV__</span><span class="k">Dividend / share</span></div>
      <div class="lede-fig"><span class="v">0</span><span class="k">Restructuring filings</span></div>
    </div>
  </header>

  <div class="tier-banner">
    <span class="lede">Curated</span>
    <p class="body">Someone read the filings. Concept choices are checked against the
    source, series crossing a renaming or a restatement are verified on overlapping
    periods, and two figures below would mislead without the correction attached to them.</p>
  </div>

  <section>
    <div class="sec-head">
      <h2>What the headline figures get wrong</h2>
      <span class="note">2 corrections</span>
    </div>
    <div class="correct-grid">
      <div class="correct">
        <span class="kpi">Debt-to-equity</span>
        <div class="pair">
          <span class="filed">29.86×</span>
          <span class="arrow">&rarr;</span>
          <span class="true">4.84×</span>
        </div>
        <p class="why">GAAP consolidates securitisation entities whose creditors have no
        claim on Redwood Trust, Inc. Recourse leverage counts only debt the parent can
        actually be pursued for.</p>
        <p class="limit"><b>And the honest limit:</b> recourse leverage has still nearly
        doubled since 2024, and part of that is equity shrinking rather than borrowing
        growing.</p>
      </div>
      <div class="correct">
        <span class="kpi">Credit loss allowance</span>
        <div class="pair">
          <span class="filed">__CLA__ &middot; __CLACH__</span>
          <span class="arrow">&rarr;</span>
          <span class="true flag">One asset, ring-fenced</span>
        </div>
        <p class="why">Effectively the entire $9.9M half-year build is a re-mark of a single
        retained interest in the Legacy Trust, a wind-down vehicle. The rollforward is
        explicit that no new securities entered an allowance position.</p>
        <p class="limit"><b>Read it as:</b> a shrinking legacy position being marked, not
        credit deteriorating across the book.</p>
      </div>
    </div>
  </section>

  <section>
    <div class="sec-head">
      <h2>Leverage, gross against recourse</h2>
      <span class="note">57 quarters &middot; CY2009Q4 &ndash; CY2026Q2</span>
    </div>
    __CHART__
    <p class="standfirst" style="font-size:15px;margin-top:14px">
      The shaded band is debt sitting on Redwood&rsquo;s balance sheet that its creditors
      cannot pursue Redwood for. The gap is the whole reason the gross line is not the
      answer &mdash; and the reason the green line, not the red one, is the number to watch.
    </p>
  </section>

  <section>
    <div class="sec-head">
      <h2>Financial position</h2>
      <span class="note">latest reported quarter &middot; QoQ vs CY2026Q1</span>
    </div>
    <div class="scroller">
      <table>
        <thead><tr>
          <th class="left">Metric</th><th class="left">Trend</th>
          <th>Latest</th><th>QoQ</th><th>Coverage</th>
        </tr></thead>
        <tbody>__ROWS__</tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="sec-head">
      <h2>Restructuring signals</h2>
      <span class="note">none filed</span>
    </div>
    <div class="quiet"><strong>No item 2.05 since 2024.</strong> A company files one when it
    commits to an exit or disposal plan. Its absence means no such plan has been disclosed
    &mdash; not that no job cuts have happened, since targeted severance expensed through
    normal operations does not trigger the requirement. The __N__ filings below are all
    item 5.02, which covers a senior officer resigning and a routine board election alike;
    the code cannot separate them, so none is treated as a warning.</div>
    <div class="sig-strip" style="margin-top:14px">__CHIPS__</div>
  </section>

  <footer>
    Sourced from SEC EDGAR &mdash; CompanyFacts, filing instance documents, and 8-K item
    codes. Independent analysis, not affiliated with or endorsed by __NAME__. Not investment
    advice. Figures are as reported and may be restated in later filings.
  </footer>
</div>
"""
main = (MAIN.replace("__CIK__", d["cik"]).replace("__NAME__", d["name"])
  .replace("__EQ__", S.fmt(K["stockholders_equity"]["latest_value"], "usd"))
  .replace("__DIV__", S.fmt(K["dividends_per_share"]["latest_value"], "usd_per_share"))
  .replace("__CLA__", S.fmt(K["credit_loss_allowance"]["latest_value"], "usd"))
  .replace("__CLACH__", S.fmt_change(S.qoq(K["credit_loss_allowance"])))
  .replace("__CHART__", S.leverage_chart(K["debt_to_equity"]["series"], rec))
  .replace("__ROWS__", "".join(rows)).replace("__CHIPS__", sig_chips)
  .replace("__N__", str(len(d["signals"]))))
open("Main.dc.html", "w").write(doc(EXTRA, main))
print("wrote Main.dc.html")
