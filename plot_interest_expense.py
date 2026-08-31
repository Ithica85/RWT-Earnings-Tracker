import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Reads the CSV already produced by get_company_facts.py — no SEC API call needed here.
CSV_PATH = "rwt_quarterly_interest_expense_complete.csv"
CHART_PATH = "rwt_interest_expense_chart.png"

# Palette (see the dataviz skill): interest expense is a cost that never goes
# negative, so — like NII and dividends — one sequential hue is enough; no
# red/green profit/loss split needed.
BLUE = "#2a78d6"

quarters = []
expense_values = []
sources = []

with open(CSV_PATH, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        quarters.append(row["quarter"])
        expense_values.append(float(row["interest_expense"]) / 1_000_000)  # USD -> $millions for readable axis ticks
        sources.append(row["source"])

# Hatch derived Q4 bars so they're visually distinguishable from SEC-reported values
hatches = ["//" if s.startswith("derived") else None for s in sources]

fig, ax = plt.subplots(figsize=(18, 6))
bars = ax.bar(quarters, expense_values, color=BLUE)

for bar, hatch in zip(bars, hatches):
    if hatch:
        bar.set_hatch(hatch)
        bar.set_edgecolor("black")

ax.set_title("Redwood Trust (RWT) — Quarterly Interest Expense")
ax.set_xlabel("Quarter")
ax.set_ylabel("Interest Expense ($M)")
ax.tick_params(axis="x", rotation=90, labelsize=7)

# Legend: hatch encodes reported vs derived (no color legend needed, single hue)
legend_handles = [
    mpatches.Patch(facecolor="white", edgecolor="black", hatch="//", label="Derived Q4 (Annual - Q1 - Q2 - Q3)"),
]
ax.legend(handles=legend_handles, loc="upper left")

fig.tight_layout()
fig.savefig(CHART_PATH, dpi=150)
print(f"Saved chart to {CHART_PATH}")
