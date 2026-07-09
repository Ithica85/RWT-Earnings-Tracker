import csv
import matplotlib.pyplot as plt

# Reads the CSV already produced by get_company_facts.py — no SEC API call needed here.
CSV_PATH = "rwt_quarterly_credit_loss_allowance.csv"
CHART_PATH = "rwt_credit_loss_allowance_chart.png"

# Palette (see the dataviz skill): Credit Loss Allowance is a single series
# tracking a magnitude over time, so it gets one sequential hue rather than the
# profit/loss red/green split used for EPS (the allowance doesn't cross zero).
BLUE = "#2a78d6"
SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"

quarters = []
allowance_values = []

with open(CSV_PATH, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        quarters.append(row["quarter"])
        allowance_values.append(float(row["credit_loss_allowance"]) / 1_000_000)  # USD -> $millions, values are small

fig, ax = plt.subplots(figsize=(18, 6))
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

# Hairline horizontal gridlines behind the line, never dashed
ax.yaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
ax.set_axisbelow(True)

ax.plot(quarters, allowance_values, color=BLUE, linewidth=2, solid_capstyle="round",
        marker="o", markersize=6, markerfacecolor=BLUE, markeredgecolor=SURFACE,
        markeredgewidth=1.2, zorder=3)

# Direct-label only the endpoint (the current allowance) — not every point
last_quarter, last_value = quarters[-1], allowance_values[-1]
ax.annotate(f"${last_value:.2f}M", xy=(last_quarter, last_value),
            xytext=(6, 6), textcoords="offset points",
            fontsize=9, fontweight="bold", color=PRIMARY_INK)

ax.set_title("Redwood Trust (RWT) — Credit Loss Allowance (AFS Debt Securities)", color=PRIMARY_INK)
ax.set_xlabel("Quarter", color=SECONDARY_INK)
ax.set_ylabel("Credit Loss Allowance ($M)", color=SECONDARY_INK)
ax.tick_params(axis="x", rotation=90, labelsize=7, colors=MUTED_INK)
ax.tick_params(axis="y", colors=MUTED_INK)

for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
for spine in ("left", "bottom"):
    ax.spines[spine].set_color(MUTED_INK)

fig.tight_layout()
fig.savefig(CHART_PATH, dpi=150, facecolor=SURFACE)
print(f"Saved chart to {CHART_PATH}")
