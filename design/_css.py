# Values copied verbatim from web/app/globals.css. Additions for the review
# (markers, sparklines, chart axes) are grouped at the end and marked.

BASE = """
  :root {
    --paper:#f2f3ef; --paper-2:#e9ebe4; --ink:#191c19; --ink-2:#4a5049;
    --ink-3:#767c74; --rule:#cfd3c9; --rule-strong:#a8aea2;
    --green:#2b5d4f; --red:#ab3226; --gold:#8a7433; --gold-wash:#efe9d6;
    --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
    --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --paper:#121412; --paper-2:#1a1d19; --ink:#e6e9e1; --ink-2:#a8afa4;
      --ink-3:#7b827a; --rule:#2c312c; --rule-strong:#414740;
      --green:#64b096; --red:#e28376; --gold:#c9ae5e; --gold-wash:#23200f;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin:0; background:var(--paper); color:var(--ink);
    font-family:var(--serif); font-size:17px; line-height:1.6;
    -webkit-font-smoothing:antialiased;
  }
  a { color:inherit; text-decoration:none; }
  a:hover { color:var(--green); }
  .wrap {
    max-width:1080px; margin:0 auto;
    padding:44px 44px 60px;
    display:flex; flex-direction:column; gap:52px;
  }
  .eyebrow {
    font-family:var(--mono); font-size:11px; letter-spacing:0.16em;
    text-transform:uppercase; color:var(--ink-3);
  }
  h1 { font-size:50px; line-height:1.05; font-weight:400; letter-spacing:-0.02em; margin:0; text-wrap:balance; }
  h2 { font-size:25px; font-weight:400; margin:0; }
  .masthead { display:flex; flex-direction:column; gap:16px; border-bottom:2px solid var(--ink); padding-bottom:22px; }
  .standfirst { font-size:18px; color:var(--ink-2); max-width:62ch; margin:0; text-wrap:pretty; }
  .sec-head { display:flex; align-items:baseline; gap:14px; border-bottom:1px solid var(--rule-strong); padding-bottom:8px; margin-bottom:20px; }
  .sec-head .note { font-family:var(--mono); font-size:11px; letter-spacing:0.1em; text-transform:uppercase; color:var(--ink-3); margin-left:auto; }
  .tier {
    display:inline-block; font-family:var(--mono); font-size:9.5px;
    letter-spacing:0.12em; text-transform:uppercase; padding:3px 8px;
    border:1px solid currentColor; border-radius:2px;
  }
  .tier-curated { color:var(--green); }
  .tier-generic { color:var(--gold); }
  .scroller { overflow-x:auto; }
  table { width:100%; border-collapse:collapse; font-size:15px; }
  th {
    font-family:var(--mono); font-size:10px; letter-spacing:0.13em;
    text-transform:uppercase; color:var(--ink-3); font-weight:400;
    text-align:right; padding:0 14px 9px; border-bottom:1px solid var(--rule-strong);
    white-space:nowrap;
  }
  th:first-child, th.left { text-align:left; }
  td { padding:13px 14px; border-bottom:1px solid var(--rule); text-align:right; vertical-align:baseline; }
  td:first-child, td.left { text-align:left; }
  tr:last-child td { border-bottom:none; }
  .num { font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:14px; white-space:nowrap; }
  .num.now { font-weight:600; font-size:15px; }
  .neg { color:var(--red); }
  .pos { color:var(--green); }
  .muted { color:var(--ink-3); }
  .kpi-name { font-weight:600; }
  .caveat {
    background:var(--gold-wash); border-left:3px solid var(--gold);
    padding:14px 18px; margin-top:10px; font-size:14.5px;
    color:var(--ink-2); max-width:78ch;
  }
  .caveat strong { color:var(--ink); display:block; margin-bottom:4px; font-size:15px; }
  .signal { display:flex; gap:16px; align-items:baseline; padding:12px 0; border-bottom:1px solid var(--rule); flex-wrap:wrap; }
  .signal:last-child { border-bottom:none; }
  .signal-date { font-family:var(--mono); font-size:13px; font-variant-numeric:tabular-nums; color:var(--ink-3); white-space:nowrap; }
  .signal-item { font-family:var(--mono); font-size:11px; letter-spacing:0.08em; padding:2px 7px; border:1px solid currentColor; border-radius:2px; white-space:nowrap; }
  .sev-high { color:var(--red); }
  .sev-medium { color:var(--ink-3); }
  .quiet { color:var(--ink-2); background:var(--paper-2); border-left:3px solid var(--rule-strong); padding:14px 18px; font-size:15px; max-width:78ch; }
  .company-grid { display:grid; gap:1px; background:var(--rule); border:1px solid var(--rule); grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); }
  .company-card { background:var(--paper); padding:20px 22px; display:flex; flex-direction:column; gap:8px; text-decoration:none; }
  .company-card .ticker { font-family:var(--mono); font-size:20px; font-weight:600; letter-spacing:-0.01em; }
  .company-card .name { font-size:15px; color:var(--ink-2); }
  .company-card .meta { font-family:var(--mono); font-size:11.5px; color:var(--ink-3); font-variant-numeric:tabular-nums; }
  footer { border-top:2px solid var(--ink); padding-top:20px; font-size:13.5px; color:var(--ink-3); max-width:76ch; }

  /* ---- added for the review, not in the shipped stylesheet ---- */
  .spark { display:block; }
  .chart { display:block; overflow:visible; }
  .ax { font-family:var(--mono); font-size:9.5px; fill:var(--ink-3); }
  .lbl { font-family:var(--mono); font-size:11.5px; font-weight:600; }
  .mark {
    display:inline-flex; align-items:center; justify-content:center;
    width:19px; height:19px; border-radius:50%;
    background:var(--red); color:var(--paper);
    font-family:var(--mono); font-size:11px; font-weight:600;
    line-height:1; flex:none; vertical-align:middle;
  }
  .mark-row { position:relative; }
  .mark-abs { position:absolute; left:-30px; top:12px; }
  .board-tag {
    font-family:var(--mono); font-size:10px; letter-spacing:0.14em;
    text-transform:uppercase; color:var(--ink-3);
    border:1px solid var(--rule-strong); border-radius:2px;
    padding:4px 9px; align-self:flex-start;
  }
  .board-tag.fix { color:var(--green); border-color:var(--green); }
"""
