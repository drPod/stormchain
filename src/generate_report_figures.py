"""Generate publication-quality figures for the report PDF."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MODEL_DIR, SIMULATION_DIR, OUTPUT_DIR, FIGURES_DIR

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# StormChain palette
COLORS = {
    "midnight": "#21295C",
    "deep_blue": "#065A82",
    "teal": "#1C7293",
    "ice": "#CADCFC",
    "coral": "#FF6B6B",
    "gold": "#F9B233",
    "slate": "#64748B",
    "light_gray": "#E5E7EB",
    "charcoal": "#2C3E50",
    "off_white": "#F5F7FA",
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 11,
    "axes.edgecolor": COLORS["slate"],
    "axes.labelcolor": COLORS["charcoal"],
    "axes.titlecolor": COLORS["midnight"],
    "axes.titleweight": "bold",
    "axes.titlesize": 14,
    "xtick.color": COLORS["charcoal"],
    "ytick.color": COLORS["charcoal"],
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
})


def fig1_baseline_comparison():
    """Bar chart: our model vs. naive baseline by K."""
    baseline = pd.read_parquet(OUTPUT_DIR / "baseline_comparison.parquet")

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(baseline))
    w = 0.38

    ax.bar(x - w/2, baseline["our_minutes_caught"]/1000, w,
           label="StormChain", color=COLORS["deep_blue"])
    ax.bar(x + w/2, baseline["naive_minutes_caught"]/1000, w,
           label="Naive Baseline", color=COLORS["slate"])

    for i, row in baseline.iterrows():
        ax.annotate(f"+{row['improvement_pct']:.0f}%",
                    xy=(i, row["our_minutes_caught"]/1000),
                    xytext=(0, 8), textcoords="offset points",
                    ha="center", fontsize=11, fontweight="bold",
                    color=COLORS["coral"])

    ax.set_xticks(x)
    ax.set_xticklabels([f"K={int(k)}" for k in baseline["k"]])
    ax.set_ylabel("Cascade Delay Minutes Caught (thousands)")
    ax.set_title("StormChain vs. Naive Baseline — Cascading Delay Capture")
    ax.legend(loc="upper left", frameon=False)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = FIGURES_DIR / "fig1_baseline_comparison.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {path}")


def fig2_case_study_timeline():
    """Hourly cascade delay on May 28, 2024."""
    case = pd.read_parquet(OUTPUT_DIR / "case_study_cascades.parquet")
    case["arr_hour"] = (case["inbound_arr_time"] // 60).astype(int)
    hourly = case.groupby("arr_hour")["total_cascade_minutes"].sum().reindex(range(6, 22), fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(hourly.index, hourly.values, color=COLORS["coral"],
                  edgecolor=COLORS["midnight"], linewidth=0.5)

    # Highlight the worst hours
    worst_idx = hourly.values.argsort()[-2:]
    for i in worst_idx:
        bars[i].set_color(COLORS["midnight"])

    ax.set_xticks(range(6, 22))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(6, 22)], rotation=45, ha="right")
    ax.set_ylabel("Cascade Delay Minutes")
    ax.set_xlabel("Hour of Inbound Arrival (local time)")
    ax.set_title("May 28, 2024 — Cascade Delay by Hour of Inbound Arrival")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="y", alpha=0.3)

    ax.annotate("Morning wave\n(overnight delays arriving)",
                xy=(7, hourly.loc[7]), xytext=(11, hourly.loc[7] * 0.9),
                fontsize=10, color=COLORS["midnight"], fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=COLORS["midnight"]))

    plt.tight_layout()
    path = FIGURES_DIR / "fig2_case_study_timeline.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {path}")


def fig3_feature_importance():
    """Top 15 XGBoost features."""
    fi = pd.read_csv(MODEL_DIR / "feature_importance.csv").head(15)
    fi = fi.iloc[::-1]  # Reverse for horizontal bar chart display

    fig, ax = plt.subplots(figsize=(9, 6))

    # Color code: DFW features in one color, others in another
    colors = [COLORS["coral"] if f.startswith("wx_dfw") else COLORS["deep_blue"]
              for f in fi["feature"]]

    ax.barh(fi["feature"], fi["importance"], color=colors)
    ax.set_xlabel("Feature Importance (gain)")
    ax.set_title("Top 15 Features Driving Cascading Delay Prediction")

    # Legend
    from matplotlib.patches import Patch
    legend = [
        Patch(color=COLORS["coral"], label="DFW hub weather"),
        Patch(color=COLORS["deep_blue"], label="Other features"),
    ]
    ax.legend(handles=legend, loc="lower right", frameon=False)
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    path = FIGURES_DIR / "fig3_feature_importance.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {path}")


def fig4_seasonal_heatmap():
    """Heatmap of top pairs by month."""
    risk = pd.read_parquet(MODEL_DIR / "risk_scores.parquet")

    # Top 25 pairs by average risk score
    pair_avg = risk.groupby(["airport_a", "airport_b"])["risk_score"].mean().nlargest(25)
    top_pairs = pair_avg.index.tolist()

    risk["pair"] = risk["airport_a"] + "-" + risk["airport_b"]
    top_labels = [f"{a}-{b}" for a, b in top_pairs]
    subset = risk[risk.apply(lambda r: (r["airport_a"], r["airport_b"]) in top_pairs, axis=1)]

    pivot = subset.pivot_table(values="risk_score", index="pair", columns="month", aggfunc="mean")
    pivot = pivot.reindex(top_labels)

    fig, ax = plt.subplots(figsize=(10, 7))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("stormchain",
        [COLORS["off_white"], COLORS["gold"], COLORS["coral"], COLORS["midnight"]])
    im = ax.imshow(pivot.values, aspect="auto", cmap=cmap, vmin=20, vmax=100)

    ax.set_xticks(range(12))
    ax.set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])
    ax.set_yticks(range(len(pivot)))
    ax.set_yticklabels(pivot.index, fontsize=9)
    ax.set_title("Top 25 Risky Airport Pairs — Risk Score by Month")

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Risk Score (0-100)")

    plt.tight_layout()
    path = FIGURES_DIR / "fig4_seasonal_heatmap.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {path}")


def fig5_us_map():
    """US map with DFW connections colored by risk."""
    risk = pd.read_parquet(MODEL_DIR / "risk_scores.parquet")
    airports = pd.read_csv("data/reference/airports.csv").set_index("iata")

    # Top 50 risky pairs (aggregated across months)
    pair_max = risk.groupby(["airport_a", "airport_b"])["risk_score"].max().nlargest(50)

    fig, ax = plt.subplots(figsize=(11, 6.5))

    # Draw continental US bounding box (approx)
    ax.set_xlim(-130, -65)
    ax.set_ylim(23, 50)
    ax.set_facecolor(COLORS["off_white"])

    # DFW coordinates
    dfw_lat, dfw_lon = 32.8998, -97.0403

    # Plot lines: each pair A→DFW→B
    drawn_airports = set()
    for (a, b), score in pair_max.items():
        for ap in [a, b]:
            if ap not in drawn_airports and ap in airports.index:
                ax.scatter(airports.loc[ap, "longitude"], airports.loc[ap, "latitude"],
                           s=30, color=COLORS["deep_blue"], zorder=3)
                ax.annotate(ap, (airports.loc[ap, "longitude"], airports.loc[ap, "latitude"]),
                            xytext=(3, 3), textcoords="offset points", fontsize=7,
                            color=COLORS["charcoal"])
                drawn_airports.add(ap)

        if a in airports.index and b in airports.index:
            # Line intensity by risk
            alpha = 0.3 + 0.7 * (score / 100)
            color = COLORS["coral"] if score > 80 else COLORS["gold"]
            ax.plot([airports.loc[a, "longitude"], dfw_lon, airports.loc[b, "longitude"]],
                    [airports.loc[a, "latitude"], dfw_lat, airports.loc[b, "latitude"]],
                    color=color, alpha=alpha, linewidth=0.8, zorder=2)

    # Highlight DFW
    ax.scatter(dfw_lon, dfw_lat, s=200, marker="*",
               color=COLORS["midnight"], edgecolor=COLORS["gold"],
               linewidth=2, zorder=10, label="DFW Hub")
    ax.annotate("DFW", (dfw_lon, dfw_lat), xytext=(8, 8),
                textcoords="offset points", fontsize=12, fontweight="bold",
                color=COLORS["midnight"])

    ax.set_title("Top 50 Risky Airport Pairs Through DFW")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(alpha=0.2)

    # Legend for risk colors
    from matplotlib.lines import Line2D
    legend = [
        Line2D([0], [0], color=COLORS["coral"], lw=2, label="Very high risk (>80)"),
        Line2D([0], [0], color=COLORS["gold"], lw=2, label="High risk (65-80)"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor=COLORS["midnight"],
               markersize=15, label="DFW Hub"),
    ]
    ax.legend(handles=legend, loc="lower left", frameon=True)

    plt.tight_layout()
    path = FIGURES_DIR / "fig5_us_map.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {path}")


def fig6_seasonal_patterns():
    """Risk score distribution by season — boxplot."""
    risk = pd.read_parquet(MODEL_DIR / "risk_scores.parquet")

    season_map = {
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring",
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Fall", 10: "Fall", 11: "Fall",
    }
    risk["season"] = risk["month"].map(season_map)
    season_order = ["Winter", "Spring", "Summer", "Fall"]

    fig, ax = plt.subplots(figsize=(9, 5))

    data = [risk[risk["season"] == s]["risk_score"].values for s in season_order]
    bp = ax.boxplot(data, labels=season_order, patch_artist=True,
                    medianprops=dict(color="white", linewidth=2),
                    flierprops=dict(marker=".", markersize=3,
                                    markerfacecolor=COLORS["slate"],
                                    markeredgecolor=COLORS["slate"]))

    season_colors = [COLORS["deep_blue"], COLORS["teal"], COLORS["coral"], COLORS["gold"]]
    for patch, color in zip(bp["boxes"], season_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)

    ax.set_ylabel("Risk Score (0-100)")
    ax.set_title("Risk Score Distribution by Season")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = FIGURES_DIR / "fig6_seasonal_patterns.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {path}")


if __name__ == "__main__":
    print("Generating report figures ...")
    fig1_baseline_comparison()
    fig2_case_study_timeline()
    fig3_feature_importance()
    fig4_seasonal_heatmap()
    fig5_us_map()
    fig6_seasonal_patterns()
    print("\nAll figures saved to outputs/figures/")
