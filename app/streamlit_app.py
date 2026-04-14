"""Streamlit dashboard for the AA Crew Sequence Weather Risk Analysis."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MODEL_DIR, SIMULATION_DIR, PROCESSED_DIR, FIGURES_DIR, OUTPUT_DIR, TOP_K_VALUES, MONTE_CARLO_TRIALS

st.set_page_config(
    page_title="StormChain — AA Sequence Risk",
    page_icon="✈️",
    layout="wide",
)

st.title("StormChain")
st.markdown("*Airline Crew Sequences Meet Bad Weather — identifying pilot sequences through DFW vulnerable to cascading delays*")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def load_risk_scores():
    path = MODEL_DIR / "risk_scores.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None

@st.cache_data(ttl=60)
def load_simulation_results():
    path = SIMULATION_DIR / "monte_carlo_results.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None

@st.cache_data
def load_feature_importance():
    path = MODEL_DIR / "feature_importance.csv"
    if path.exists():
        return pd.read_csv(path)
    return None

@st.cache_data
def load_roc_curve():
    path = MODEL_DIR / "roc_curve.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None

@st.cache_data
def load_pr_curve():
    path = MODEL_DIR / "pr_curve.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None

@st.cache_data
def load_test_predictions():
    path = MODEL_DIR / "test_predictions.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None

@st.cache_data
def load_airports():
    path = PROCESSED_DIR.parent / "reference" / "airports.csv"
    if path.exists():
        return pd.read_csv(path)
    return None

@st.cache_data(ttl=60)
def load_avoid_list():
    path = OUTPUT_DIR / "avoid_list.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None

@st.cache_data(ttl=60)
def load_swap_recommendations():
    path = OUTPUT_DIR / "swap_recommendations.csv"
    if path.exists():
        return pd.read_csv(path)
    return None

@st.cache_data(ttl=60)
def load_baseline_comparison():
    path = OUTPUT_DIR / "baseline_comparison.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None

@st.cache_data(ttl=60)
def load_case_study():
    path = OUTPUT_DIR / "case_study_cascades.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None

@st.cache_data(ttl=60)
def load_seasonal_summary():
    path = OUTPUT_DIR / "seasonal_summary.csv"
    if path.exists():
        return pd.read_csv(path)
    return None


# Load data
risk_scores = load_risk_scores()
sim_results = load_simulation_results()
importance = load_feature_importance()
airports = load_airports()
avoid_list = load_avoid_list()
swap_recs = load_swap_recommendations()
baseline = load_baseline_comparison()
case_study = load_case_study()
seasonal_summary = load_seasonal_summary()

if risk_scores is None:
    st.error("No risk scores found. Run the pipeline first: `python run_pipeline.py`")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

with st.sidebar:
    st.header("Filters")
    month_options = ["All Months"] + [MONTH_NAMES[i] for i in range(1, 13)]
    selected_month_name = st.selectbox("Month", month_options)
    if selected_month_name == "All Months":
        selected_month = None
    else:
        selected_month = [k for k, v in MONTH_NAMES.items() if v == selected_month_name][0]

    min_overlap = st.slider("Min overlap days", 5, 100, 10)
    top_n = st.slider("Show top N pairs", 10, 500, 50)

# Filter data
filtered = risk_scores[risk_scores["n_overlap_days"] >= min_overlap].copy()
if selected_month:
    filtered = filtered[filtered["month"] == selected_month]

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Pair Explorer", "Recommendations", "US Map",
    "Model Performance", "Impact Analysis",
    "Case Study", "Seasonal Heatmap",
])

# ---------------------------------------------------------------------------
# Tab 1: Pair Explorer
# ---------------------------------------------------------------------------

with tab1:
    st.subheader("Airport Pair Risk Explorer")

    all_airports_sorted = sorted(
        set(risk_scores["airport_a"].unique()) | set(risk_scores["airport_b"].unique())
    )

    col1, col2 = st.columns(2)
    with col1:
        airport_a = st.selectbox("Airport A", all_airports_sorted, index=0)
    with col2:
        airport_b = st.selectbox("Airport B", all_airports_sorted,
                                 index=min(1, len(all_airports_sorted) - 1))

    # Find pair (either direction)
    pair_data = risk_scores[
        ((risk_scores["airport_a"] == airport_a) & (risk_scores["airport_b"] == airport_b)) |
        ((risk_scores["airport_a"] == airport_b) & (risk_scores["airport_b"] == airport_a))
    ].sort_values("month")

    if len(pair_data) > 0:
        col1, col2 = st.columns(2)
        with col1:
            # Monthly risk score bar chart
            fig = px.bar(
                pair_data, x="month", y="risk_score",
                title=f"Monthly Risk Score: {airport_a} - DFW - {airport_b}",
                labels={"month": "Month", "risk_score": "Risk Score (0-100)"},
                color="risk_score",
                color_continuous_scale="RdYlGn_r",
            )
            fig.update_xaxes(tickvals=list(range(1, 13)),
                             ticktext=list(MONTH_NAMES.values()))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Key metrics
            avg_risk = pair_data["risk_score"].mean()
            max_risk = pair_data["risk_score"].max()
            peak_month = MONTH_NAMES[pair_data.loc[pair_data["risk_score"].idxmax(), "month"]]

            st.metric("Average Risk Score", f"{avg_risk:.1f}")
            st.metric("Peak Risk Score", f"{max_risk:.1f}")
            st.metric("Peak Month", peak_month)
            st.metric("Joint Weather Delay Prob (avg)",
                       f"{pair_data['joint_weather_delay_prob'].mean():.3f}")
            if "precip_correlation" in pair_data.columns:
                st.metric("Precip Correlation (avg)",
                           f"{pair_data['precip_correlation'].mean():.3f}")
    else:
        st.info(f"No data for pair {airport_a} - {airport_b}")

# ---------------------------------------------------------------------------
# Tab 2: Recommendations (Avoid List + Swaps)
# ---------------------------------------------------------------------------

with tab2:
    st.subheader("Scheduling Recommendations")

    rec_tab_a, rec_tab_b, rec_tab_c = st.tabs(["Avoid List", "Swap Recommendations", "Seasonal Summary"])

    with rec_tab_a:
        if avoid_list is not None:
            st.markdown("**Pairs to avoid in pilot sequences, by season:**")
            season_filter = st.selectbox("Filter by season", ["All"] + sorted(avoid_list["season"].unique()))
            display = avoid_list if season_filter == "All" else avoid_list[avoid_list["season"] == season_filter]
            st.dataframe(
                display[["season", "airport_a", "airport_b", "risk_score", "reason"]].head(100),
                use_container_width=True,
            )
            st.metric("Total Recommendations", f"{len(avoid_list)} pair-season combinations")
        else:
            st.info("Run `python src/recommendations.py` to generate avoid list")

    with rec_tab_b:
        if swap_recs is not None:
            st.markdown("**Safe alternatives for each flagged pair:**")
            st.dataframe(
                swap_recs[["season", "avoid_origin", "avoid_dest", "avoid_risk",
                           "swap_dest", "swap_risk", "risk_reduction"]].head(50),
                use_container_width=True,
            )
            avg_reduction = swap_recs["risk_reduction"].mean()
            st.metric("Average Risk Reduction per Swap", f"{avg_reduction:.0f} points")
        else:
            st.info("Run recommendations to generate swap suggestions")

    with rec_tab_c:
        if seasonal_summary is not None:
            for season in seasonal_summary["season"].unique():
                st.markdown(f"**{season}**")
                season_data = seasonal_summary[seasonal_summary["season"] == season]
                st.dataframe(
                    season_data[["rank", "airport_a", "airport_b", "avg_risk", "geographic_pattern"]],
                    use_container_width=True, hide_index=True,
                )
        else:
            st.info("Run recommendations to generate seasonal summary")

    # Baseline comparison
    if baseline is not None:
        st.subheader("Model vs. Naive Baseline")
        st.markdown("*How much better is our model than simply avoiding two individually high-delay airports?*")

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Our Model", x=baseline["k"], y=baseline["our_minutes_caught"],
                             marker_color="green"))
        fig.add_trace(go.Bar(name="Naive Baseline", x=baseline["k"], y=baseline["naive_minutes_caught"],
                             marker_color="lightgray"))
        fig.update_layout(
            title="Cascade Minutes Caught: Our Model vs. Naive Baseline",
            xaxis_title="Number of Pairs Flagged (K)",
            yaxis_title="Cascade Minutes Caught",
            barmode="group",
        )
        st.plotly_chart(fig, use_container_width=True)

        best_improvement = baseline["improvement_pct"].max()
        st.success(f"**Our model catches up to {best_improvement:.0f}% more cascading delay minutes than the naive approach at the same K.**")

# ---------------------------------------------------------------------------
# Tab 7: Seasonal Heatmap (moved from old tab2)
# ---------------------------------------------------------------------------

with tab7:
    st.subheader("Seasonal Risk Heatmap")

    top_pairs = filtered.nlargest(top_n, "risk_score")

    if len(top_pairs) > 0:
        # Create pair label
        top_pairs["pair"] = top_pairs["airport_a"] + " - " + top_pairs["airport_b"]

        # Pivot for heatmap
        unique_pairs = top_pairs.groupby("pair")["risk_score"].mean().nlargest(min(30, top_n)).index
        heatmap_data = risk_scores.copy()
        heatmap_data["pair"] = heatmap_data["airport_a"] + " - " + heatmap_data["airport_b"]
        heatmap_data = heatmap_data[heatmap_data["pair"].isin(unique_pairs)]

        pivot = heatmap_data.pivot_table(
            values="risk_score", index="pair", columns="month", aggfunc="mean"
        )
        pivot.columns = [MONTH_NAMES[m] for m in pivot.columns]

        fig = px.imshow(
            pivot,
            title="Airport Pair Risk by Month (Top Pairs)",
            labels={"x": "Month", "y": "Airport Pair", "color": "Risk Score"},
            color_continuous_scale="RdYlGn_r",
            aspect="auto",
        )
        fig.update_layout(height=max(400, len(unique_pairs) * 25))
        st.plotly_chart(fig, use_container_width=True)

        # Top pairs table
        st.subheader(f"Top {min(top_n, len(top_pairs))} Risky Pairs")
        display_cols = ["airport_a", "airport_b", "month", "risk_score",
                        "joint_weather_delay_prob", "thunderstorm_co_occurrence"]
        available = [c for c in display_cols if c in top_pairs.columns]
        st.dataframe(top_pairs[available].head(top_n), use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 3: US Map
# ---------------------------------------------------------------------------

with tab3:
    st.subheader("US Airport Risk Map")

    if airports is not None and len(filtered) > 0:
        # Get top risky pairs for the map
        map_pairs = filtered.nlargest(min(top_n, 200), "risk_score")

        # Airport locations
        airport_dict = airports.set_index("iata").to_dict("index")

        # Create lines for each risky pair
        lines_lat = []
        lines_lon = []
        line_colors = []
        hover_texts = []

        for _, row in map_pairs.iterrows():
            a, b = row["airport_a"], row["airport_b"]
            a_info = airport_dict.get(a)
            b_info = airport_dict.get(b)
            if not a_info or not b_info:
                continue

            # DFW coords
            dfw_lat, dfw_lon = 32.8998, -97.0403

            # Line from A to DFW
            lines_lat += [a_info["latitude"], dfw_lat, None]
            lines_lon += [a_info["longitude"], dfw_lon, None]

            # Line from DFW to B
            lines_lat += [dfw_lat, b_info["latitude"], None]
            lines_lon += [dfw_lon, b_info["longitude"], None]

            line_colors.append(row["risk_score"])
            hover_texts.append(f"{a} - DFW - {b}: Risk {row['risk_score']:.1f}")

        fig = go.Figure()

        # Add lines (connections)
        fig.add_trace(go.Scattergeo(
            lat=lines_lat, lon=lines_lon,
            mode="lines",
            line=dict(width=1, color="red"),
            opacity=0.3,
            showlegend=False,
        ))

        # Add airport markers
        unique_airports = set(map_pairs["airport_a"]) | set(map_pairs["airport_b"])
        ap_lats, ap_lons, ap_names, ap_sizes = [], [], [], []
        for ap in unique_airports:
            info = airport_dict.get(ap)
            if info:
                ap_lats.append(info["latitude"])
                ap_lons.append(info["longitude"])
                ap_names.append(ap)
                # Size by how many risky pairs this airport appears in
                count = ((map_pairs["airport_a"] == ap) | (map_pairs["airport_b"] == ap)).sum()
                ap_sizes.append(max(6, min(20, count)))

        fig.add_trace(go.Scattergeo(
            lat=ap_lats, lon=ap_lons,
            text=ap_names,
            mode="markers+text",
            textposition="top center",
            marker=dict(size=ap_sizes, color="blue", opacity=0.7),
            showlegend=False,
        ))

        # DFW marker (larger)
        fig.add_trace(go.Scattergeo(
            lat=[32.8998], lon=[-97.0403],
            text=["DFW"],
            mode="markers+text",
            textposition="bottom center",
            marker=dict(size=15, color="gold", symbol="star", line=dict(width=2, color="black")),
            name="DFW Hub",
        ))

        fig.update_geos(
            scope="usa",
            showland=True, landcolor="lightgray",
            showlakes=True, lakecolor="lightblue",
        )
        fig.update_layout(
            title=f"Top {min(top_n, len(map_pairs))} Risky Airport Pairs Through DFW",
            height=600,
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 4: Model Performance
# ---------------------------------------------------------------------------

with tab4:
    st.subheader("XGBoost Model Performance")

    col1, col2 = st.columns(2)

    roc_data = load_roc_curve()
    pr_data = load_pr_curve()

    with col1:
        if roc_data is not None:
            fig = px.area(roc_data, x="fpr", y="tpr",
                          title="ROC Curve",
                          labels={"fpr": "False Positive Rate", "tpr": "True Positive Rate"})
            fig.add_shape(type="line", x0=0, x1=1, y0=0, y1=1,
                          line=dict(dash="dash", color="gray"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ROC curve data not yet available")

    with col2:
        if pr_data is not None:
            fig = px.area(pr_data, x="recall", y="precision",
                          title="Precision-Recall Curve",
                          labels={"recall": "Recall", "precision": "Precision"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("PR curve data not yet available")

    # Feature importance
    if importance is not None:
        st.subheader("Top 20 Feature Importances")
        top_imp = importance.head(20)
        fig = px.bar(top_imp, x="importance", y="feature", orientation="h",
                     title="XGBoost Feature Importance (Gain)",
                     labels={"importance": "Importance", "feature": "Feature"})
        fig.update_layout(yaxis=dict(autorange="reversed"), height=500)
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 5: Simulation Results
# ---------------------------------------------------------------------------

with tab5:
    st.subheader("Impact Analysis: Delay Savings from Avoiding Risky Pairs")

    if sim_results is not None and "k" in sim_results.columns:
        # New format: retrospective analysis
        col1, col2 = st.columns(2)

        with col1:
            # Line chart: K vs dollar savings
            fig = px.line(
                sim_results, x="k", y="dollar_savings",
                title="Total Preventable Delay Cost by Pairs Avoided",
                markers=True,
                labels={"k": "Number of Risky Pairs Avoided", "dollar_savings": "Savings ($)"},
            )
            fig.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Bar chart: % of cascading events prevented
            fig = px.bar(
                sim_results, x="k", y="pct_events_prevented",
                title="% of Cascading Delay Events Prevented",
                labels={"k": "Risky Pairs Avoided", "pct_events_prevented": "Events Prevented (%)"},
                color="pct_events_prevented",
                color_continuous_scale="Greens",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Summary table
        display_df = sim_results[["k", "prevented_events", "total_cascade_events",
                                   "pct_events_prevented", "prevented_minutes",
                                   "dollar_savings"]].copy()
        display_df.columns = ["Pairs Avoided", "Events Prevented", "Total Events",
                              "% Prevented", "Minutes Saved", "Dollar Savings"]
        display_df["Dollar Savings"] = display_df["Dollar Savings"].apply(lambda x: f"${x:,.0f}")
        display_df["% Prevented"] = display_df["% Prevented"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_df, use_container_width=True)

        # Monthly breakdown
        monthly_path = SIMULATION_DIR / "monthly_breakdown.parquet"
        if monthly_path.exists():
            monthly = pd.read_parquet(monthly_path)
            best_k = sim_results["k"].max()
            monthly_best = monthly[monthly["k"] == best_k]

            MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            monthly_best = monthly_best.copy()
            monthly_best["month_name"] = monthly_best["month"].apply(lambda m: MONTH_LABELS[m-1])

            fig = px.bar(
                monthly_best, x="month_name", y="dollar_savings",
                title=f"Monthly Savings Breakdown (K={best_k})",
                labels={"month_name": "Month", "dollar_savings": "Savings ($)"},
                color="dollar_savings", color_continuous_scale="RdYlGn",
            )
            fig.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",")
            st.plotly_chart(fig, use_container_width=True)

        # Headline metrics — both upper bound and adjusted
        best_row = sim_results.loc[sim_results["k"].idxmax()]
        years_in_data = max(1, len(set(pd.to_datetime(
            pd.read_parquet(PROCESSED_DIR / "flights_dfw.parquet", columns=["Year"])["Year"]
        ).unique())))

        annual_upper = best_row["dollar_savings"] / years_in_data
        has_adjusted = "adjusted_savings" in sim_results.columns
        annual_adjusted = best_row.get("adjusted_savings", annual_upper) / years_in_data if has_adjusted else annual_upper

        st.success(
            f"**By avoiding the top {int(best_row['k'])} risky airport pairs, "
            f"American Airlines could prevent {best_row['pct_events_prevented']:.1f}% "
            f"of cascading weather delays.**"
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Upper Bound (worst-case scheduling)", f"${annual_upper:,.0f}/year")
        with col2:
            st.metric("Adjusted Estimate (random assignment)", f"${annual_adjusted:,.0f}/year")

        if has_adjusted:
            st.caption(
                "Upper bound assumes every flagged pair was assigned every impacted day. "
                "Adjusted estimate scales by the probability that a specific pair is actually "
                "assigned on any given day (~7%), which is more realistic."
            )
    else:
        st.info("Simulation results not yet available. Run the pipeline first.")

# ---------------------------------------------------------------------------
# Tab 6: Case Study — May 28, 2024
# ---------------------------------------------------------------------------

with tab6:
    st.subheader("Case Study: May 28, 2024")
    st.markdown("*The worst cascading delay day in our dataset*")

    if case_study is not None:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Weather-Delayed Inbound", "172 flights")
        with col2:
            st.metric("Delayed Outbound (>15min)", "471 flights")
        with col3:
            st.metric("Cascading Sequences", f"{len(case_study):,}")
        with col4:
            total_cost = case_study["total_cascade_minutes"].sum() * 75
            st.metric("Estimated Cascade Cost", f"${total_cost:,.0f}")

        st.markdown("---")

        # Timeline
        case_study["arr_hour"] = (case_study["inbound_arr_time"] // 60).astype(int)
        hourly = case_study.groupby("arr_hour").agg(
            cascades=("total_cascade_minutes", "size"),
            total_delay=("total_cascade_minutes", "sum"),
        ).reset_index()
        hourly["hour_label"] = hourly["arr_hour"].apply(lambda h: f"{h:02d}:00")

        fig = px.bar(hourly, x="hour_label", y="total_delay",
                     title="Cascade Delay by Hour of Inbound Arrival",
                     labels={"hour_label": "Hour", "total_delay": "Total Cascade Minutes"},
                     color="total_delay", color_continuous_scale="Reds")
        st.plotly_chart(fig, use_container_width=True)

        # Top pairs
        st.subheader("Top Cascading Pairs on This Day")
        pair_summary = case_study.groupby(["origin", "dest"]).agg(
            sequences=("total_cascade_minutes", "size"),
            total_cascade=("total_cascade_minutes", "sum"),
            avg_cascade=("total_cascade_minutes", "mean"),
            risk_score=("risk_score", "mean"),
        ).sort_values("total_cascade", ascending=False).head(15).reset_index()

        pair_summary["was_flagged"] = pair_summary["risk_score"] >= 65
        pair_summary["status"] = pair_summary["was_flagged"].map({True: "Flagged by model", False: "MISSED"})

        fig = px.bar(pair_summary, x=pair_summary["origin"] + "→" + pair_summary["dest"],
                     y="total_cascade", color="status",
                     title="Top 15 Cascading Pairs — Flagged vs. Missed",
                     labels={"x": "Pair (Origin→Dest)", "total_cascade": "Total Cascade Minutes"},
                     color_discrete_map={"Flagged by model": "green", "MISSED": "red"})
        st.plotly_chart(fig, use_container_width=True)

        # What our model caught
        flagged = case_study[case_study["risk_score"] >= 65]
        missed = case_study[case_study["risk_score"] < 65]
        flagged_pct = len(flagged) / max(len(case_study), 1) * 100
        flagged_min = flagged["total_cascade_minutes"].sum()
        total_min = case_study["total_cascade_minutes"].sum()

        st.info(
            f"**Our model flagged {len(flagged):,} of {len(case_study):,} cascading sequences "
            f"({flagged_pct:.1f}%), covering {flagged_min:,.0f} of {total_min:,.0f} cascade minutes "
            f"({flagged_min/max(total_min,1)*100:.1f}%).**"
        )
    else:
        st.info("Run `python src/case_study.py` to generate case study data.")
