import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Reads the CSV already produced by get_company_facts.py — no SEC API call needed here.
CSV_PATH = "rwt_quarterly_net_income_complete.csv"
CHART_PATH = "rwt_net_income_chart.png"

quarters = []
net_income_values = []
sources = []

with open(CSV_PATH, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        quarters.append(row["quarter"])
        net_income_values.append(float(row["net_income"]) / 1_000_000)  # USD -> $millions for readable axis ticks
        sources.append(row["source"])

# Color each bar by sign so the chart reads as a profit/loss trend at a glance,
# same convention as plot_eps.py (net income can go negative, unlike NII/dividends)
colors = ["#2ca02c" if v >= 0 else "#d62728" for v in net_income_values]

# Hatch derived Q4 bars so they're visually distinguishable from SEC-reported values
hatches = ["//" if s.startswith("derived") else None for s in sources]

fig, ax = plt.subplots(figsize=(18, 6))
bars = ax.bar(quarters, net_income_values, color=colors)

for bar, hatch in zip(bars, hatches):
    if hatch:
        bar.set_hatch(hatch)
        bar.set_edgecolor("black")

ax.axhline(0, color="black", linewidth=0.8)
ax.set_title("Redwood Trust (RWT) — Quarterly Net Income")
ax.set_xlabel("Quarter")
ax.set_ylabel("Net Income ($M)")
ax.tick_params(axis="x", rotation=90, labelsize=7)

# If one quarter's magnitude dwarfs the rest (e.g. CY2020Q1's COVID write-down),
# a linear axis crushes every other bar flat. Clip the axis to the bulk of the
# data and annotate any bar that gets cut off with its real value.
magnitudes = sorted(abs(v) for v in net_income_values)
largest, second_largest = magnitudes[-1], magnitudes[-2]
if largest > second_largest * 3:
    margin = second_largest * 1.3
    ax.set_ylim(-margin, margin)
    for quarter, val in zip(quarters, net_income_values):
        if abs(val) > margin:
            y_text, va = (-margin * 0.92, "bottom") if val < 0 else (margin * 0.92, "top")
            ax.annotate(f"{val:.1f}", xy=(quarter, y_text), ha="center", va=va,
                        fontsize=7, fontweight="bold")

# Legend: color encodes profit/loss, hatch encodes reported vs derived
legend_handles = [
    mpatches.Patch(color="#2ca02c", label="Positive Net Income"),
    mpatches.Patch(color="#d62728", label="Negative Net Income"),
    mpatches.Patch(facecolor="white", edgecolor="black", hatch="//", label="Derived Q4 (Annual - Q1 - Q2 - Q3)"),
]
ax.legend(handles=legend_handles, loc="upper left")

fig.tight_layout()
fig.savefig(CHART_PATH, dpi=150)
print(f"Saved chart to {CHART_PATH}")
