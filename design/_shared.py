"""Shared pieces for the design-review artboards.

Every value here is lifted from web/app/globals.css so the mockups match the
built site exactly rather than approximately.
"""
import json, csv, os

ROOT = "/Users/danielmcdermott/Documents/Projects/RWT"

# ---------- data ----------

def company(t):
    d = json.load(open(os.path.join(ROOT, "web/data/%s.json" % t)))
    for c in d.get("caveats", []):
        k = d["kpis"].get(c["kpi"])
        if k:
            k.setdefault("caveats", []).append(c)
    return d

def index():
    return json.load(open(os.path.join(ROOT, "web/data/index.json")))

def recourse():
    with open(os.path.join(ROOT, "rwt_quarterly_recourse_leverage.csv")) as f:
        return list(csv.DictReader(f))

# ---------- formatting (mirrors web/lib/data.ts exactly) ----------

def fmt(v, unit):
    if v is None: return "—"
    if unit == "usd_per_share":
        return ("−" if v < 0 else "") + "$%.2f" % abs(v)
    if unit == "multiple":
        return "%.2f×" % v
    if unit == "usd":
        a, s = abs(v), ("−" if v < 0 else "")
        if a >= 1e9: return "%s$%.2fB" % (s, a/1e9)
        if a >= 1e6: return "%s$%.1fM" % (s, a/1e6)
        return "%s$%s" % (s, "{:,}".format(int(a)))
    return "{:,}".format(v)

def qoq(kpi):
    s = kpi.get("series")
    if not s or len(s) < 2: return None
    p, c = s[-2]["value"], s[-1]["value"]
    if p == 0: return None
    if (p < 0) != (c < 0): return None
    return (c - p) / abs(p) * 100.0

def fmt_change(ch):
    if ch is None: return "—"
    r = round(ch, 1)
    if r == 0: return "0.0%"
    return ("+" if r > 0 else "−") + "%.1f%%" % abs(r)

# ---------- charts ----------

def sparkline(series, color, w=132, h=30, pad=3.0, zero=False):
    vals = [p["value"] for p in series]
    if not vals: return ""
    lo, hi = min(vals), max(vals)
    if zero: lo, hi = min(lo, 0.0), max(hi, 0.0)
    rng = (hi - lo) or 1.0
    n = len(vals)
    def Y(v): return h - pad - (h - 2*pad) * (v - lo) / rng
    def X(i): return pad + (w - 2*pad) * (i / (n - 1) if n > 1 else 0)
    pts = " ".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in enumerate(vals))
    base = ""
    if zero and lo < 0 < hi:
        zy = Y(0.0)
        base = ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--rule-strong)" '
                'stroke-width="1" stroke-dasharray="2 2"/>' % (pad, zy, w - pad, zy))
    end = '<circle cx="%.1f" cy="%.1f" r="2.1" fill="%s"/>' % (X(n-1), Y(vals[-1]), color)
    return ('<svg class="spark" viewBox="0 0 %d %d" width="%d" height="%d" '
            'preserveAspectRatio="none" aria-hidden="true">%s'
            '<polyline points="%s" fill="none" stroke="%s" stroke-width="1.4" '
            'stroke-linejoin="round" stroke-linecap="round"/>%s</svg>'
            % (w, h, w, h, base, pts, color, end))

def leverage_chart(de_series, rec_rows, w=1000, h=280):
    """Gross vs recourse leverage, mirroring plot_recourse_leverage.py."""
    L, R, T, B = 46.0, 78.0, 18.0, 30.0
    qs = [p["quarter"] for p in de_series]
    idx = {q: i for i, q in enumerate(qs)}
    n = len(qs)
    hi = 32.0
    def X(i): return L + (w - L - R) * (i / (n - 1))
    def Y(v): return h - B - (h - B - T) * (v / hi)

    gross = [(X(i), Y(p["value"])) for i, p in enumerate(de_series)]
    rec = [(X(idx[r["quarter"]]), Y(float(r["recourse_leverage"])), idx[r["quarter"]])
           for r in rec_rows if r["quarter"] in idx]

    # shaded non-recourse band over the overlap
    band = ""
    if rec:
        top = [(x, Y(de_series[i]["value"])) for x, _, i in rec]
        bot = list(reversed([(x, y) for x, y, _ in rec]))
        pth = " ".join("%.1f,%.1f" % p for p in top + bot)
        band = '<polygon points="%s" fill="var(--rule)" opacity="0.55"/>' % pth

    grid = "".join(
        '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--rule)" stroke-width="1"/>'
        '<text x="%.1f" y="%.1f" class="ax" text-anchor="end">%d×</text>'
        % (L, Y(v), w - R, Y(v), L - 8, Y(v) + 3.5, v)
        for v in (0, 10, 20, 30))

    gl = " ".join("%.1f,%.1f" % p for p in gross)
    rl = " ".join("%.1f,%.1f" % (x, y) for x, y, _ in rec)

    labels = ""
    if rec:
        gx, gy = gross[-1]
        rx, ry = rec[-1][0], rec[-1][1]
        labels = (
            '<text x="%.1f" y="%.1f" class="lbl" fill="var(--red)">29.86× gross</text>'
            '<text x="%.1f" y="%.1f" class="lbl" fill="var(--green)">4.84× recourse</text>'
            % (gx + 8, gy + 4, rx + 8, ry + 4))

    ticks = ""
    for q in ("CY2009Q4", "CY2015Q4", "CY2020Q1", "CY2024Q2", "CY2026Q2"):
        if q in idx:
            x = X(idx[q])
            ticks += ('<text x="%.1f" y="%.1f" class="ax" text-anchor="middle">%s</text>'
                      % (x, h - 10, q.replace("CY", "")))

    return ('<svg viewBox="0 0 %d %d" width="100%%" height="%d" class="chart" role="img" '
            'aria-label="Gross debt-to-equity against recourse leverage, 2009 to 2026">'
            '%s%s'
            '<polyline points="%s" fill="none" stroke="var(--red)" stroke-width="1.8" '
            'stroke-linejoin="round"/>'
            '<polyline points="%s" fill="none" stroke="var(--green)" stroke-width="2.2" '
            'stroke-linejoin="round"/>%s%s</svg>'
            % (w, h, h, grid, band, gl, rl, labels, ticks))
