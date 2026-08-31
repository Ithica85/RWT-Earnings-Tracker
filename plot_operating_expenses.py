import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Reads the CSV already produced by get_operating_expenses.py — no SEC call here.
CSV_PATH = "rwt_quarterly_operating_expenses.csv"
CHART_PATH = "rwt_operating_expenses_chart.png"

# Palette (see the dataviz skill): operating expenses never go negative, so one
# sequential hue is enough — same treatment as NII and interest expense.
BLUE = "#2a78d6"

quarters = []
expense_values = []
sources = []

with open(CSV_PATH, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        quarters.append(row["quarter"])
        expense_values.append(float(row["operating_expenses"]) / 1_000_000)  # USD -> $millions for readable axis ticks
        sources.append(row["source"])

# Hatch derived Q4 bars, same convention as the other duration KPIs. Note the
# `source` column here has three values, not two: quarters from CY2024Q3 onward
# are summed from the four expense components because filings stopped tagging a
# total. Those are still reported figures — only the annual-minus-quarters ones
# are inferred — so only "derived" gets hatched.
hatches = ["//" if s.startswith("derived") else None for s in sources]

fig, ax = plt.subplots(figsize=(18, 6))
bars = ax.bar(quarters, expense_values, color=BLUE)

for bar, hatch in zip(bars, hatches):
    if hatch:
        bar.set_hatch(hatch)
        bar.set_edgecolor("black")

ax.set_title("Redwood Trust (RWT) — Quarterly Operating Expenses")
ax.set_xlabel("Quarter")
ax.set_ylabel("Operating Expenses ($M)")
ax.tick_params(axis="x", rotation=90, labelsize=7)

legend_handles = [
    mpatches.Patch(facecolor="white", edgecolor="black", hatch="//", label="Derived Q4 (Annual - Q1 - Q2 - Q3)"),
]
ax.legend(handles=legend_handles, loc="upper left")

fig.tight_layout()
fig.savefig(CHART_PATH, dpi=150)
print(f"Saved chart to {CHART_PATH}")
