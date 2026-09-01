"""Artboards 1-2: the shipped pages, reproduced from the real data, marked up."""
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

def doc(css_extra, body):
    return DOC.replace("__CSS__", BASE + css_extra).replace("__BODY__", body)

def mark(n):
    return '<span class="mark">%d</span>' % n

# ---------------------------------------------------------------- company page

d = S.company("rwt")
rows = []
for key, k in d["kpis"].items():
    if not k.get("available", True):
        rows.append('<tr><td class="kpi-name">%s</td>'
                    '<td class="num muted" colspan="3">not reported by this filer</td></tr>' % k["label"])
        continue
    ch = S.qoq(k)
    neg = (k.get("latest_value") or 0) < 0
    marker = ""
    if key == "eps":
        marker = " " + mark(6)
    rows.append(
        '<tr><td class="kpi-name">%s</td>'
        '<td class="num now %s">%s</td>'
        '<td class="num muted">%s%s</td>'
        '<td class="num muted">%dq from %s</td></tr>'
        % (k["label"], "neg" if neg else "", S.fmt(k.get("latest_value"), k.get("unit")),
           S.fmt_change(ch), marker, k.get("quarters", 0), k.get("first", "")))
    for c in k.get("caveats", []):
        extra = mark(2) + " " if key == "debt_to_equity" else ""
        tail = ""
        if key == "debt_to_equity":
            tail = ('<div style="margin-top:9px;font-family:var(--mono);font-size:12px;'
                    'color:var(--red)">%s the only figure that corrects the headline — 4.84× — '
                    'is prose inside this box. <code>companion: "recourse_leverage"</code> is '
                    'declared in the data and never exported as a KPI.</div>' % mark(3))
        rows.append('<tr><td colspan="4" style="padding-top:0"><div class="caveat">'
                    '<strong>%s%s</strong>%s%s</div></td></tr>'
                    % (extra, c["headline"], c["detail"], tail))

sig_rows = "".join(
    '<div class="signal"><span class="signal-date">%s</span>'
    '<span class="signal-item sev-%s">%s</span>'
    '<span style="flex:1;min-width:18ch">%s</span>'
    '<a class="signal-date" href="#">filing ↗</a></div>'
    % (s["date"], s["severity"], s["item"], s["meaning"]) for s in d["signals"])

high = [s for s in d["signals"] if s["severity"] == "high"]
has205 = [s for s in d["signals"] if s["item"] == "2.05"]

body_company = """
<div class="wrap">
  <div class="board-tag">Shipped today &middot; app/company/[ticker]/page.tsx</div>

  <header class="masthead">
    <div class="eyebrow">&larr; All companies &middot; CIK __CIK__</div>
    <h1>__NAME__</h1>
    <p class="standfirst">
      <span class="tier tier-curated">curated</span>
      Concept choices checked against the filings; series crossing a renaming or
      restatement verified against overlapping periods.
    </p>
  </header>

  <section>
    <div class="sec-head">
      <h2>Financial position __M1__</h2>
      <span class="note">latest reported quarter</span>
    </div>
    <div style="font-family:var(--mono);font-size:12px;color:var(--red);margin:-10px 0 16px">
      __M1B__ 662 points of quarterly history sit in rwt.json. Ten of them render.
      There is no chart in the app and no chart library in package.json.
    </div>
    <div class="scroller">
      <table>
        <thead><tr><th class="left">Metric</th><th>Latest</th><th>QoQ</th><th>Coverage</th></tr></thead>
        <tbody>__ROWS__</tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="sec-head">
      <h2>Restructuring signals __M5__</h2>
      <span class="note">8-K disclosures since 2024</span>
    </div>
    __QUIET__
    <div style="margin-top:18px">__SIGS__</div>
    __MEDIUM__
  </section>

  <footer>
    Sourced from SEC EDGAR &mdash; CompanyFacts, filing instance documents, and
    8-K item codes. Independent analysis, not affiliated with or endorsed by
    __NAME__. Not investment advice. Figures are as reported and may be restated
    in later filings.
  </footer>
</div>
"""

quiet = "" if has205 else (
    '<div class="quiet"><strong>No item 2.05 filed.</strong> A company must file one '
    'when it commits to an exit or disposal plan &mdash; a restructuring, in the '
    'SEC&rsquo;s language. Its absence means no such plan has been disclosed. It does '
    'not mean no job cuts have happened: targeted severance expensed through normal '
    'operations does not trigger the requirement.</div>')

medium = ""
if not high and d["signals"]:
    medium = ('<p class="standfirst" style="margin-top:16px">All %d are medium severity. '
              'Item 5.02 covers both a senior officer resigning and a routine board '
              'election &mdash; the code alone cannot separate them, so none is treated '
              'as a warning.</p>' % len(d["signals"]))

body_company = (body_company
    .replace("__CIK__", d["cik"]).replace("__NAME__", d["name"])
    .replace("__ROWS__", "".join(rows)).replace("__SIGS__", sig_rows)
    .replace("__QUIET__", quiet).replace("__MEDIUM__", medium)
    .replace("__M1__", mark(1)).replace("__M1B__", mark(1))
    .replace("__M5__", mark(5)))

open("CurrentCompany.dc.html", "w").write(doc("", body_company))

# ------------------------------------------------------------------ index page

idx = S.index()
curated = sum(1 for c in idx if c["tier"] == "curated")
cards = "".join(
    '<a class="company-card" href="#">'
    '<span class="ticker">%s</span>'
    '<span class="name">%s</span>'
    '<span class="tier tier-%s">%s</span>'
    '<span class="meta">%d metrics &middot; %d signals%s<br>through %s</span></a>'
    % (c["ticker"], c["name"], c["tier"], c["tier"], c["kpi_count"], c["signal_count"],
       (" &middot; %d caveats" % c["caveat_count"]) if c["caveat_count"] else "",
       c["latest_quarter"] or "—")
    for c in idx)

body_index = """
<div class="wrap">
  <div class="board-tag">Shipped today &middot; app/page.tsx</div>

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
      <h2>Companies __M7__</h2>
      <span class="note">__CUR__ curated &middot; __GEN__ generic</span>
    </div>
    <div style="font-family:var(--mono);font-size:12px;color:var(--red);margin:-10px 0 16px">
      __M7B__ Five companies, no way to see two of them at once. Every card is a
      dead end that links away. __M4B__ The tier badge &mdash; the difference between a
      checked figure and one nobody has read &mdash; is 9.5px, the smallest type here.
    </div>
    <div class="company-grid">__CARDS__</div>
  </section>

  <section>
    <div class="sec-head"><h2>What the two tiers mean __M4__</h2></div>
    <p class="standfirst" style="margin-bottom:1em">
      <span class="tier tier-curated">curated</span> &mdash; someone read the filings.
      Concept choices are checked, series that cross a renaming or a restatement are
      verified against overlapping periods, and the figures that mislead carry a correction.
    </p>
    <p class="standfirst">
      <span class="tier tier-generic">generic</span> &mdash; the obvious concepts, pulled
      automatically, with nobody having looked. Useful as a starting point and not as an
      answer. On the one company that has been curated, the generic reading of leverage was
      wrong by roughly six times.
    </p>
  </section>

  <footer>
    Built from SEC EDGAR: the CompanyFacts API, filing instance documents, and 8-K item
    codes. Independent analysis, not affiliated with or endorsed by any company covered.
    Not investment advice. Figures are as reported and may be restated in later filings.
  </footer>
</div>
"""
body_index = (body_index
    .replace("__CARDS__", cards).replace("__CUR__", str(curated))
    .replace("__GEN__", str(len(idx) - curated))
    .replace("__M7__", mark(7)).replace("__M7B__", mark(7))
    .replace("__M4__", mark(4)).replace("__M4B__", mark(4)))

open("CurrentIndex.dc.html", "w").write(doc("", body_index))
print("wrote CurrentCompany.dc.html, CurrentIndex.dc.html")
