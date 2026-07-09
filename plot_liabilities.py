import csv
import matplotlib.pyplot as plt

# Reads the CSV already produced by get_company_facts.py — no SEC API call needed here.
CSV_PATH = "rwt_quarterly_liabilities.csv"
CHART_PATH = "rwt_liabilities_chart.png"

# Palette (see the dataviz skill): Total Liabilities is a single series tracking
# a magnitude over time, so it gets one sequential hue rather than the
# profit/loss red/green split used for EPS (liabilities don't cross zero).
BLUE = "#2a78d6"
SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"

quarters = []
liabilities_values = []

with open(CSV_PATH, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        quarters.append(row["quarter"])
        liabilities_values.append(float(row["total_liabilities"]) / 1_000_000_000)  # USD -> $billions for readable axis ticks

fig, ax = plt.subplots(figsize=(18, 6))
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

# Hairline horizontal gridlines behind the line, never dashed
ax.yaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
ax.set_axisbelow(True)

ax.plot(quarters, liabilities_values, color=BLUE, linewidth=2, solid_capstyle="round",
        marker="o", markersize=6, markerfacecolor=BLUE, markeredgecolor=SURFACE,
        markeredgewidth=1.2, zorder=3)

# Direct-label only the endpoint (the current Total Liabilities) — not every point
last_quarter, last_value = quarters[-1], liabilities_values[-1]
ax.annotate(f"${last_value:.2f}B", xy=(last_quarter, last_value),
            xytext=(6, 6), textcoords="offset points",
            fontsize=9, fontweight="bold", color=PRIMARY_INK)

ax.set_title("Redwood Trust (RWT) — Total Liabilities", color=PRIMARY_INK)
ax.set_xlabel("Quarter", color=SECONDARY_INK)
ax.set_ylabel("Total Liabilities ($B)", color=SECONDARY_INK)
ax.tick_params(axis="x", rotation=90, labelsize=7, colors=MUTED_INK)
ax.tick_params(axis="y", colors=MUTED_INK)

for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
for spine in ("left", "bottom"):
    ax.spines[spine].set_color(MUTED_INK)

fig.tight_layout()
fig.savefig(CHART_PATH, dpi=150, facecolor=SURFACE)
print(f"Saved chart to {CHART_PATH}")
