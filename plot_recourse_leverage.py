import csv

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Reads the CSV produced by get_recourse_leverage.py — no SEC call needed here.
CSV_PATH = "rwt_quarterly_recourse_leverage.csv"
CHART_PATH = "rwt_recourse_leverage_chart.png"

# Palette (see the dataviz skill): two series that are different *things*, not
# steps of one magnitude, so this is a categorical assignment. The pair was
# validated with the skill's validate_palette.js against this surface —
# all six checks pass, worst adjacent CVD separation ΔE 24.7 (protan).
#
# Both series are dimensionless multiples, so they legitimately share one
# y-axis. This is not a dual-axis chart — the whole point is that the two
# numbers are directly comparable and the gap between them is enormous.
ORANGE = "#eb6834"   # gross debt-to-equity — the misleading headline figure
BLUE = "#2a78d6"     # recourse leverage — what Redwood is actually liable for
SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"
GAP_FILL = "#e8e6df"

quarters = []
recourse = []
gross = []

with open(CSV_PATH, newline="") as f:
    for row in csv.DictReader(f):
        quarters.append(row["quarter"])
        recourse.append(float(row["recourse_leverage"]))
        gross.append(float(row["gross_debt_to_equity"]))

fig, ax = plt.subplots(figsize=(14, 7))
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

ax.yaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
ax.set_axisbelow(True)

x = range(len(quarters))

# The band between the two lines is consolidated non-recourse debt — liabilities
# GAAP puts on the balance sheet that Redwood Trust, Inc. cannot be pursued for.
# Shading it makes the gap a quantity rather than empty space. No texture: the
# band is a derived area rather than a third series, and the two real series
# carry identity through position, validated hues, the legend and end labels.
ax.fill_between(x, recourse, gross, color=GAP_FILL, zorder=1, linewidth=0.0)

ax.plot(x, gross, color=ORANGE, linewidth=2, solid_capstyle="round",
        marker="o", markersize=8, markerfacecolor=ORANGE,
        markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)

ax.plot(x, recourse, color=BLUE, linewidth=2, solid_capstyle="round",
        marker="o", markersize=8, markerfacecolor=BLUE,
        markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)

# Direct-label only the endpoints, per the project's sparing-label convention.
ax.annotate(f"{gross[-1]:.1f}x", xy=(len(quarters) - 1, gross[-1]),
            xytext=(8, 2), textcoords="offset points",
            fontsize=11, fontweight="bold", color=PRIMARY_INK)
ax.annotate(f"{recourse[-1]:.1f}x", xy=(len(quarters) - 1, recourse[-1]),
            xytext=(8, -4), textcoords="offset points",
            fontsize=11, fontweight="bold", color=PRIMARY_INK)

# Name the band once, in text ink rather than a series color.
mid = len(quarters) // 2
ax.annotate("consolidated non-recourse debt\n(securitisation entities — no claim on Redwood)",
            xy=(mid, (gross[mid] + recourse[mid]) / 2),
            ha="center", va="center", fontsize=9, color=SECONDARY_INK,
            linespacing=1.5, zorder=4)

# A legend is required for two series; identity is never color-alone.
ax.legend(handles=[
    Line2D([], [], color=ORANGE, linewidth=2, marker="o", markersize=8,
           markeredgecolor=SURFACE, markeredgewidth=2,
           label="Gross debt-to-equity (total liabilities / equity)"),
    Line2D([], [], color=BLUE, linewidth=2, marker="o", markersize=8,
           markeredgecolor=SURFACE, markeredgewidth=2,
           label="Recourse leverage (recourse debt / equity)"),
    Patch(facecolor=GAP_FILL, edgecolor="#cbc7ba",
          label="Non-recourse — consolidated but not Redwood's obligation"),
], loc="upper left", frameon=False, fontsize=9, labelcolor=SECONDARY_INK)

ax.set_title(
    "Redwood Trust (RWT) — Gross Leverage vs. Recourse Leverage",
    color=PRIMARY_INK, fontsize=14, pad=14,
)
ax.set_xlabel("Quarter", color=SECONDARY_INK)
ax.set_ylabel("Multiple of stockholders' equity", color=SECONDARY_INK)

ax.set_xticks(list(x))
ax.set_xticklabels(quarters)
ax.tick_params(axis="x", rotation=90, labelsize=8, colors=MUTED_INK)
ax.tick_params(axis="y", colors=MUTED_INK)
ax.set_ylim(bottom=0)

for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
for spine in ("left", "bottom"):
    ax.spines[spine].set_color(MUTED_INK)

fig.tight_layout()
fig.savefig(CHART_PATH, dpi=150, facecolor=SURFACE)
print(f"Saved chart to {CHART_PATH}")
