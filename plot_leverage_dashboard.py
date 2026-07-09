import csv
import math
import matplotlib.pyplot as plt

# Reads CSVs already produced by get_company_facts.py — no SEC API call needed here.
# Combines three already-charted KPIs (assets, liabilities, debt-to-equity) into
# one dashboard so the leverage story reads as a single view instead of three
# separate charts.
ASSETS_CSV = "rwt_quarterly_assets.csv"
LIABILITIES_CSV = "rwt_quarterly_liabilities.csv"
DEBT_TO_EQUITY_CSV = "rwt_quarterly_debt_to_equity.csv"
CHART_PATH = "rwt_leverage_dashboard.png"

# Palette (see the dataviz skill): Assets and Liabilities are two distinct
# entities plotted together, so they get categorical hues (slot 1 blue, slot 8
# orange — validated for CVD separation) rather than a sequential single hue.
# Debt-to-equity is alone in its own panel, so it stays single-hue blue,
# consistent with plot_assets.py / plot_liabilities.py / plot_debt_to_equity.py.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
EQUITY_FILL = "#c3c2b7"  # muted, not a series color -- this is a derived area, not a KPI
SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"


def read_csv_as_dict(path, value_key):
    with open(path, newline="") as f:
        return {row["quarter"]: float(row[value_key]) for row in csv.DictReader(f)}


assets_by_quarter = read_csv_as_dict(ASSETS_CSV, "total_assets")
liabilities_by_quarter = read_csv_as_dict(LIABILITIES_CSV, "total_liabilities")
debt_to_equity_by_quarter = read_csv_as_dict(DEBT_TO_EQUITY_CSV, "debt_to_equity")

# Assets and liabilities cover identical quarters (both are instant measures
# with full coverage); debt-to-equity has a few gaps where StockholdersEquity
# wasn't framed. Use assets' quarters as the master timeline and fill
# debt-to-equity gaps with NaN so the line breaks at the gap instead of
# connecting straight across it or misaligning with the other two panels.
quarters = sorted(assets_by_quarter)
x = range(len(quarters))

assets_b = [assets_by_quarter[q] / 1_000_000_000 for q in quarters]
liabilities_b = [liabilities_by_quarter[q] / 1_000_000_000 for q in quarters]
debt_to_equity = [debt_to_equity_by_quarter.get(q, math.nan) for q in quarters]

fig, (ax_balance, ax_ratio) = plt.subplots(
    2, 1, figsize=(18, 9), sharex=True, height_ratios=[2, 1],
)
fig.patch.set_facecolor(SURFACE)

for ax in (ax_balance, ax_ratio):
    ax.set_facecolor(SURFACE)
    ax.yaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(MUTED_INK)
    ax.tick_params(axis="y", colors=MUTED_INK)

# --- Top panel: Total Assets vs Total Liabilities ---------------------------

# Shade the gap between the two lines to visualize implied equity (Assets -
# Liabilities). Muted gray, not a series color -- it's a derived area, not a
# third KPI, so it doesn't compete with the two real series for identity.
ax_balance.fill_between(x, liabilities_b, assets_b, color=EQUITY_FILL, alpha=0.25,
                         zorder=1, label="Implied Equity (Assets − Liabilities)")

ax_balance.plot(x, assets_b, color=BLUE, linewidth=2, solid_capstyle="round",
                 marker="o", markersize=5, markerfacecolor=BLUE, markeredgecolor=SURFACE,
                 markeredgewidth=1, zorder=3, label="Total Assets")
ax_balance.plot(x, liabilities_b, color=ORANGE, linewidth=2, solid_capstyle="round",
                 marker="o", markersize=5, markerfacecolor=ORANGE, markeredgecolor=SURFACE,
                 markeredgewidth=1, zorder=3, label="Total Liabilities")

# Direct-label only the endpoints, not every point
ax_balance.annotate(f"${assets_b[-1]:.2f}B", xy=(x[-1], assets_b[-1]),
                     xytext=(6, 4), textcoords="offset points",
                     fontsize=9, fontweight="bold", color=PRIMARY_INK)
ax_balance.annotate(f"${liabilities_b[-1]:.2f}B", xy=(x[-1], liabilities_b[-1]),
                     xytext=(6, -10), textcoords="offset points",
                     fontsize=9, fontweight="bold", color=PRIMARY_INK)

ax_balance.set_title("Redwood Trust (RWT) — Leverage Dashboard", color=PRIMARY_INK, fontsize=14, pad=12)
ax_balance.set_ylabel("$B", color=SECONDARY_INK)
ax_balance.legend(loc="upper left", frameon=False, labelcolor=SECONDARY_INK)

# --- Bottom panel: Debt-to-Equity ratio --------------------------------------

ax_ratio.plot(x, debt_to_equity, color=BLUE, linewidth=2, solid_capstyle="round",
              marker="o", markersize=5, markerfacecolor=BLUE, markeredgecolor=SURFACE,
              markeredgewidth=1, zorder=3)

last_valid_idx = max(i for i, v in enumerate(debt_to_equity) if not math.isnan(v))
ax_ratio.annotate(f"{debt_to_equity[last_valid_idx]:.1f}x",
                   xy=(x[last_valid_idx], debt_to_equity[last_valid_idx]),
                   xytext=(6, 6), textcoords="offset points",
                   fontsize=9, fontweight="bold", color=PRIMARY_INK)

ax_ratio.set_ylabel("Debt / Equity", color=SECONDARY_INK)
ax_ratio.set_xlabel("Quarter", color=SECONDARY_INK)
ax_ratio.set_xticks(list(x))
ax_ratio.set_xticklabels(quarters, rotation=90, fontsize=7, color=MUTED_INK)

fig.tight_layout()
fig.savefig(CHART_PATH, dpi=150, facecolor=SURFACE)
print(f"Saved chart to {CHART_PATH}")
