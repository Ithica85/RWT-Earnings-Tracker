import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Reads the CSV already produced by get_company_facts.py — no SEC API call needed here.
CSV_PATH = "rwt_quarterly_nii_complete.csv"
CHART_PATH = "rwt_nii_chart.png"

# Palette (see the dataviz skill): net interest income never goes negative for
# RWT historically, so — like BVPS and dividends — one sequential hue is
# enough; no red/green profit/loss split needed.
BLUE = "#2a78d6"

quarters = []
nii_values = []
sources = []

with open(CSV_PATH, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        quarters.append(row["quarter"])
        nii_values.append(float(row["net_interest_income"]) / 1_000_000)  # USD -> $millions for readable axis ticks
        sources.append(row["source"])

# Hatch derived Q4 bars so they're visually distinguishable from SEC-reported values
hatches = ["//" if s.startswith("derived") else None for s in sources]

fig, ax = plt.subplots(figsize=(18, 6))
bars = ax.bar(quarters, nii_values, color=BLUE)

for bar, hatch in zip(bars, hatches):
    if hatch:
        bar.set_hatch(hatch)
        bar.set_edgecolor("black")

ax.set_title("Redwood Trust (RWT) — Quarterly Net Interest Income")
ax.set_xlabel("Quarter")
ax.set_ylabel("Net Interest Income ($M)")
ax.tick_params(axis="x", rotation=90, labelsize=7)

# Legend: hatch encodes reported vs derived (no color legend needed, single hue)
legend_handles = [
    mpatches.Patch(facecolor="white", edgecolor="black", hatch="//", label="Derived Q4 (Annual - Q1 - Q2 - Q3)"),
]
ax.legend(handles=legend_handles, loc="upper left")

fig.tight_layout()
fig.savefig(CHART_PATH, dpi=150)
print(f"Saved chart to {CHART_PATH}")
