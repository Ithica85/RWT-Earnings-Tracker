import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Reads the CSV already produced by get_company_facts.py — no SEC API call needed here.
CSV_PATH = "rwt_quarterly_dividends_complete.csv"
CHART_PATH = "rwt_dividends_chart.png"

# Palette (see the dataviz skill): dividends per share never go negative, so
# unlike EPS this doesn't need a profit/loss red/green split -- one sequential
# hue (the same blue used for the BVPS chart) is enough.
BLUE = "#2a78d6"

quarters = []
dividend_values = []
sources = []

with open(CSV_PATH, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        quarters.append(row["quarter"])
        dividend_values.append(float(row["dividend_per_share"]))
        sources.append(row["source"])

# Hatch derived Q4 bars so they're visually distinguishable from SEC-reported values
hatches = ["//" if s.startswith("derived") else None for s in sources]

fig, ax = plt.subplots(figsize=(18, 6))
bars = ax.bar(quarters, dividend_values, color=BLUE)

for bar, hatch in zip(bars, hatches):
    if hatch:
        bar.set_hatch(hatch)
        bar.set_edgecolor("black")

ax.set_title("Redwood Trust (RWT) — Quarterly Dividends Per Common Share")
ax.set_xlabel("Quarter")
ax.set_ylabel("Dividend Per Share (USD)")
ax.tick_params(axis="x", rotation=90, labelsize=7)

# Legend: hatch encodes reported vs derived (no color legend needed, single hue)
legend_handles = [
    mpatches.Patch(facecolor="white", edgecolor="black", hatch="//", label="Derived Q4 (Annual - Q1 - Q2 - Q3)"),
]
ax.legend(handles=legend_handles, loc="upper left")

fig.tight_layout()
fig.savefig(CHART_PATH, dpi=150)
print(f"Saved chart to {CHART_PATH}")
