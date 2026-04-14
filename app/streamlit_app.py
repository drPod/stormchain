"""StormChain Operations Command Center — tactical dashboard for crew sequence risk."""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MODEL_DIR, SIMULATION_DIR, PROCESSED_DIR, OUTPUT_DIR

# =========================================================================
# PAGE CONFIG
# =========================================================================
st.set_page_config(
    page_title="StormChain OCC",
    page_icon="⛈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================================
# BRAND PALETTE
# =========================================================================
C = {
    "bg": "#0A1026",
    "panel": "#141B3A",
    "panel_light": "#1F2950",
    "midnight": "#21295C",
    "deep_blue": "#065A82",
    "teal": "#1C7293",
    "ice": "#CADCFC",
    "coral": "#FF6B6B",
    "gold": "#F9B233",
    "green": "#50C878",
    "white": "#FFFFFF",
    "muted": "#8B93B5",
    "border": "#2A3563",
}

# =========================================================================
# CUSTOM CSS — kill Streamlit chrome, dark OCC aesthetic
# =========================================================================
st.markdown(f"""
<style>
    /* Hide Streamlit defaults */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .stDeployButton {{display: none;}}

    /* Dark background */
    .stApp {{
        background-color: {C['bg']};
        color: {C['white']};
    }}
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 100%;
    }}

    /* Typography */
    h1, h2, h3, h4 {{
        font-family: 'Georgia', serif !important;
        color: {C['white']} !important;
        letter-spacing: -0.5px;
    }}
    p, div, span, label {{
        color: {C['ice']};
    }}

    /* Brand header */
    .brand-header {{
        background: linear-gradient(90deg, {C['midnight']} 0%, {C['deep_blue']} 100%);
        padding: 16px 24px;
        border-radius: 4px;
        border-left: 4px solid {C['coral']};
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .brand-title {{
        font-family: 'Georgia', serif;
        font-size: 28px;
        font-weight: bold;
        color: {C['white']};
        margin: 0;
        letter-spacing: 1px;
    }}
    .brand-subtitle {{
        font-size: 11px;
        color: {C['ice']};
        letter-spacing: 3px;
        text-transform: uppercase;
    }}
    .status-dot {{
        display: inline-block;
        width: 10px;
        height: 10px;
        background: {C['green']};
        border-radius: 50%;
        margin-right: 8px;
        box-shadow: 0 0 8px {C['green']};
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
    }}

    /* KPI Cards */
    .kpi-card {{
        background: {C['panel']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        padding: 16px 20px;
        min-height: 110px;
        position: relative;
        overflow: hidden;
    }}
    .kpi-card.alert {{ border-left: 3px solid {C['coral']}; }}
    .kpi-card.warn {{ border-left: 3px solid {C['gold']}; }}
    .kpi-card.ok {{ border-left: 3px solid {C['green']}; }}
    .kpi-card.info {{ border-left: 3px solid {C['teal']}; }}
    .kpi-label {{
        font-size: 10px;
        letter-spacing: 2px;
        color: {C['muted']};
        text-transform: uppercase;
        margin-bottom: 4px;
    }}
    .kpi-value {{
        font-family: 'Georgia', serif;
        font-size: 38px;
        font-weight: bold;
        color: {C['white']};
        line-height: 1;
    }}
    .kpi-value.coral {{ color: {C['coral']}; }}
    .kpi-value.gold {{ color: {C['gold']}; }}
    .kpi-value.teal {{ color: {C['ice']}; }}
    .kpi-detail {{
        font-size: 12px;
        color: {C['muted']};
        margin-top: 6px;
    }}

    /* Panels */
    .ops-panel {{
        background: {C['panel']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        padding: 16px;
        height: 100%;
    }}
    .panel-title {{
        font-family: 'Georgia', serif;
        font-size: 14px;
        color: {C['white']};
        font-weight: bold;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid {C['border']};
    }}

    /* Risk feed rows */
    .feed-row {{
        padding: 8px 0;
        border-bottom: 1px solid {C['border']};
        font-size: 13px;
    }}
    .feed-row:last-child {{ border-bottom: none; }}
    .pair-label {{
        font-family: 'Consolas', monospace;
        color: {C['white']};
        font-weight: bold;
    }}
    .risk-badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: bold;
        margin-left: 8px;
    }}
    .risk-badge.critical {{ background: {C['coral']}; color: {C['white']}; }}
    .risk-badge.high {{ background: {C['gold']}; color: {C['midnight']}; }}
    .risk-badge.mod {{ background: {C['teal']}; color: {C['white']}; }}

    /* Streamlit widget styling */
    .stSelectbox label, .stSlider label, .stSelectSlider label {{
        color: {C['muted']} !important;
        font-size: 11px !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
    }}

    /* Selectbox closed state */
    .stSelectbox > div > div,
    [data-baseweb="select"] > div,
    [data-baseweb="select"] div[role="combobox"] {{
        background-color: {C['panel']} !important;
        border: 1px solid {C['border']} !important;
        color: {C['white']} !important;
    }}
    [data-baseweb="select"] * {{
        color: {C['white']} !important;
    }}
    /* Selectbox open dropdown menu */
    [data-baseweb="popover"] {{
        background-color: {C['panel']} !important;
    }}
    [data-baseweb="popover"] [role="listbox"],
    [data-baseweb="menu"] {{
        background-color: {C['panel']} !important;
        border: 1px solid {C['border']} !important;
    }}
    [data-baseweb="menu"] li,
    [data-baseweb="popover"] [role="option"] {{
        background-color: {C['panel']} !important;
        color: {C['ice']} !important;
    }}
    [data-baseweb="menu"] li:hover,
    [data-baseweb="popover"] [role="option"]:hover,
    [aria-selected="true"] {{
        background-color: {C['midnight']} !important;
        color: {C['white']} !important;
    }}
    /* Slider track and thumb */
    .stSlider [data-baseweb="slider"] div[role="slider"] {{
        background-color: {C['coral']} !important;
        border-color: {C['coral']} !important;
    }}
    .stSlider [data-baseweb="slider"] > div > div > div {{
        background: {C['coral']} !important;
    }}
    /* Metric widget */
    [data-testid="stMetricValue"] {{
        color: {C['white']} !important;
        font-family: 'Georgia', serif !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {C['muted']} !important;
    }}
    [data-testid="stMetricDelta"] {{
        color: {C['gold']} !important;
    }}
    /* Dataframes */
    [data-testid="stDataFrame"] {{
        background-color: {C['panel']} !important;
    }}
    [data-testid="stDataFrame"] [role="columnheader"] {{
        background-color: {C['midnight']} !important;
        color: {C['gold']} !important;
    }}
    [data-testid="stDataFrame"] [role="gridcell"] {{
        background-color: {C['panel']} !important;
        color: {C['ice']} !important;
    }}
    /* Caption text */
    .stCaption, [data-testid="stCaptionContainer"] {{
        color: {C['muted']} !important;
    }}

    /* Expanders for deep analysis */
    .stExpander {{
        background: {C['panel']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        margin-bottom: 12px;
    }}
    .streamlit-expanderHeader {{
        color: {C['white']} !important;
        font-family: 'Georgia', serif !important;
    }}

    /* Tables */
    .dataframe {{
        color: {C['ice']} !important;
        background: {C['panel']} !important;
    }}
    .dataframe th {{
        background: {C['midnight']} !important;
        color: {C['gold']} !important;
        font-weight: bold;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 1px;
    }}
    .dataframe td {{
        background: {C['panel']} !important;
        color: {C['ice']} !important;
        border-color: {C['border']} !important;
    }}
</style>
""", unsafe_allow_html=True)


# =========================================================================
# DATA LOADING
# =========================================================================
@st.cache_data(ttl=300)
def load_risk_scores():
    return pd.read_parquet(MODEL_DIR / "risk_scores.parquet")

@st.cache_data(ttl=300)
def load_avoid_list():
    path = OUTPUT_DIR / "avoid_list.parquet"
    return pd.read_parquet(path) if path.exists() else None

@st.cache_data(ttl=300)
def load_baseline():
    path = OUTPUT_DIR / "baseline_comparison.parquet"
    return pd.read_parquet(path) if path.exists() else None

@st.cache_data(ttl=300)
def load_case_study():
    path = OUTPUT_DIR / "case_study_cascades.parquet"
    return pd.read_parquet(path) if path.exists() else None

@st.cache_data(ttl=300)
def load_airports():
    return pd.read_csv(PROCESSED_DIR.parent / "reference" / "airports.csv")

@st.cache_data(ttl=300)
def load_sim_results():
    path = SIMULATION_DIR / "monte_carlo_results.parquet"
    return pd.read_parquet(path) if path.exists() else None

@st.cache_data(ttl=300)
def load_feature_importance():
    path = MODEL_DIR / "feature_importance.csv"
    return pd.read_csv(path) if path.exists() else None

@st.cache_data(ttl=300)
def load_swap_recs():
    path = OUTPUT_DIR / "swap_recommendations.csv"
    return pd.read_csv(path) if path.exists() else None

@st.cache_data(ttl=300)
def load_roc_curve():
    path = MODEL_DIR / "roc_curve.parquet"
    return pd.read_parquet(path) if path.exists() else None

@st.cache_data(ttl=300)
def load_pr_curve():
    path = MODEL_DIR / "pr_curve.parquet"
    return pd.read_parquet(path) if path.exists() else None

@st.cache_data(ttl=300)
def load_monthly_breakdown():
    path = SIMULATION_DIR / "monthly_breakdown.parquet"
    return pd.read_parquet(path) if path.exists() else None

@st.cache_data(ttl=300)
def load_seasonal_summary():
    path = OUTPUT_DIR / "seasonal_summary.csv"
    return pd.read_csv(path) if path.exists() else None

@st.cache_data(ttl=300)
def load_top_cascading_pairs():
    path = SIMULATION_DIR / "top_cascading_pairs.parquet"
    return pd.read_parquet(path) if path.exists() else None


risk_scores = load_risk_scores()
avoid_list = load_avoid_list()
baseline = load_baseline()
case_study = load_case_study()
airports = load_airports()
sim_results = load_sim_results()
importance = load_feature_importance()
swap_recs = load_swap_recs()
roc_curve = load_roc_curve()
pr_curve = load_pr_curve()
monthly_breakdown = load_monthly_breakdown()
seasonal_summary = load_seasonal_summary()
top_cascading_pairs = load_top_cascading_pairs()

# =========================================================================
# HEADER
# =========================================================================
now = datetime.now()
current_month = st.session_state.get("current_month", now.month)

col_title, col_time = st.columns([3, 1])
with col_title:
    st.markdown(f"""
    <div class="brand-header">
        <div>
            <p class="brand-title">⛈️  STORMCHAIN OCC</p>
            <p class="brand-subtitle">Crew Sequence Weather Risk — Operations Command Center</p>
        </div>
        <div style="text-align: right;">
            <p style="color: {C['white']}; margin: 0; font-size: 14px;">
                <span class="status-dot"></span>SYSTEM NOMINAL
            </p>
            <p style="color: {C['muted']}; margin: 0; font-size: 11px;">
                {now.strftime('%a %b %d, %Y · %H:%M')} LOCAL
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =========================================================================
# CONTROLS
# =========================================================================
ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 3])

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
with ctrl1:
    selected_month = st.selectbox(
        "Focus month",
        options=list(range(1, 13)),
        format_func=lambda m: MONTH_NAMES[m-1],
        index=current_month - 1,
    )
with ctrl2:
    k_threshold = st.select_slider(
        "Avoid top K pairs",
        options=[50, 100, 200, 500],
        value=200,
    )
with ctrl3:
    st.markdown(f"""
    <div style='padding-top: 26px; text-align: right; color: {C['muted']}; font-size: 11px; letter-spacing: 2px;'>
        DATA · 842K FLIGHTS · 3.5M WEATHER · 3.3M METAR · 2019–2024
    </div>
    """, unsafe_allow_html=True)

# Filter scores to selected month
month_scores = risk_scores[risk_scores["month"] == selected_month].copy()
month_scores = month_scores.sort_values("risk_score", ascending=False)

# =========================================================================
# KPI SCOREBOARD STRIP
# =========================================================================
k1, k2, k3, k4 = st.columns(4)

# KPI 1: Critical pairs this month
critical_count = (month_scores["risk_score"] >= 80).sum()
k1.markdown(f"""
<div class="kpi-card alert">
    <p class="kpi-label">CRITICAL PAIRS · {MONTH_NAMES[selected_month-1].upper()}</p>
    <p class="kpi-value coral">{critical_count}</p>
    <p class="kpi-detail">risk score ≥ 80</p>
</div>
""", unsafe_allow_html=True)

# KPI 2: Model performance
k2.markdown(f"""
<div class="kpi-card info">
    <p class="kpi-label">MODEL AUC-ROC</p>
    <p class="kpi-value teal">0.81</p>
    <p class="kpi-detail">+78% vs. naive baseline at K=200</p>
</div>
""", unsafe_allow_html=True)

# KPI 3: Savings at current K
if sim_results is not None:
    sim_row = sim_results[sim_results["k"] == k_threshold]
    if len(sim_row) > 0:
        savings_upper = sim_row["dollar_savings"].iloc[0] / 5
        savings_adj = sim_row.get("adjusted_savings", sim_row["dollar_savings"]).iloc[0] / 5
        k3.markdown(f"""
        <div class="kpi-card ok">
            <p class="kpi-label">ANNUAL SAVINGS · K={k_threshold}</p>
            <p class="kpi-value gold">${savings_upper/1e6:.1f}M</p>
            <p class="kpi-detail">${savings_adj/1e3:.0f}K adjusted estimate</p>
        </div>
        """, unsafe_allow_html=True)

# KPI 4: Avoid list size for current month
month_avoid = 0
if avoid_list is not None:
    month_avoid = len(avoid_list[avoid_list["month"] == selected_month])
k4.markdown(f"""
<div class="kpi-card warn">
    <p class="kpi-label">AVOID LIST · {MONTH_NAMES[selected_month-1].upper()}</p>
    <p class="kpi-value gold">{month_avoid}</p>
    <p class="kpi-detail">pair recommendations for this month</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# =========================================================================
# MAIN GRID: Map + Risk Feed
# =========================================================================
map_col, feed_col = st.columns([2.2, 1])

with map_col:
    st.markdown(f"""
    <p class="panel-title" style='margin-bottom: 8px;'>
        RADAR · TOP {k_threshold} RISKY PAIRS THROUGH DFW · {MONTH_NAMES[selected_month-1].upper()}
    </p>
    """, unsafe_allow_html=True)

    top_k_month = month_scores.head(k_threshold)
    airport_dict = airports.set_index("iata").to_dict("index")
    dfw_lat, dfw_lon = 32.8998, -97.0403

    fig = go.Figure()

    # Risk lines
    drawn_airports = set()
    for _, row in top_k_month.iterrows():
        a, b = row["airport_a"], row["airport_b"]
        a_info = airport_dict.get(a)
        b_info = airport_dict.get(b)
        if not a_info or not b_info:
            continue
        drawn_airports.add(a)
        drawn_airports.add(b)

        risk = row["risk_score"]
        color = C["coral"] if risk >= 80 else C["gold"] if risk >= 65 else C["teal"]
        width = 2.5 if risk >= 80 else 1.8 if risk >= 65 else 1.2

        fig.add_trace(go.Scattergeo(
            lat=[a_info["latitude"], dfw_lat, b_info["latitude"]],
            lon=[a_info["longitude"], dfw_lon, b_info["longitude"]],
            mode="lines",
            line=dict(width=width, color=color),
            opacity=0.7,
            hoverinfo="skip",
            showlegend=False,
        ))

    # Airport markers
    ap_lats, ap_lons, ap_names = [], [], []
    for ap in drawn_airports:
        info = airport_dict.get(ap)
        if info:
            ap_lats.append(info["latitude"])
            ap_lons.append(info["longitude"])
            ap_names.append(ap)

    fig.add_trace(go.Scattergeo(
        lat=ap_lats, lon=ap_lons, text=ap_names,
        mode="markers+text",
        textposition="top center",
        textfont=dict(color=C["ice"], size=9, family="Consolas"),
        marker=dict(size=6, color=C["deep_blue"], line=dict(width=1, color=C["ice"])),
        hoverinfo="text",
        showlegend=False,
    ))

    # DFW Hub
    fig.add_trace(go.Scattergeo(
        lat=[dfw_lat], lon=[dfw_lon], text=["DFW"],
        mode="markers+text",
        textposition="bottom center",
        textfont=dict(color=C["gold"], size=14, family="Georgia"),
        marker=dict(size=18, color=C["gold"], symbol="star",
                    line=dict(width=2, color=C["white"])),
        hoverinfo="text",
        name="DFW Hub",
        showlegend=False,
    ))

    fig.update_geos(
        scope="usa",
        showland=True,
        landcolor=C["panel"],
        showlakes=True,
        lakecolor=C["bg"],
        showcountries=False,
        showsubunits=True,
        subunitcolor=C["border"],
        showcoastlines=True,
        coastlinecolor=C["border"],
        bgcolor=C["bg"],
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=420,
        paper_bgcolor=C["bg"],
        plot_bgcolor=C["bg"],
    )
    st.plotly_chart(fig, use_container_width=True)

    # Legend strip
    st.markdown(f"""
    <div style='text-align: center; font-size: 11px; color: {C['muted']}; letter-spacing: 2px;'>
        <span style='color: {C['coral']}; font-weight: bold;'>━━</span> CRITICAL (≥80) &nbsp;&nbsp;&nbsp;
        <span style='color: {C['gold']}; font-weight: bold;'>━━</span> HIGH (65–80) &nbsp;&nbsp;&nbsp;
        <span style='color: {C['teal']}; font-weight: bold;'>━━</span> MODERATE (&lt;65) &nbsp;&nbsp;&nbsp;
        <span style='color: {C['gold']};'>★</span> DFW HUB
    </div>
    """, unsafe_allow_html=True)


with feed_col:
    st.markdown(f"""
    <p class="panel-title" style='margin-bottom: 8px;'>
        RISK FEED · LIVE
    </p>
    """, unsafe_allow_html=True)

    # Airport city lookup
    city_lookup = airports.set_index("iata")["city"].to_dict()

    st.markdown("<div style='background: " + C['panel'] + "; border: 1px solid " + C['border'] +
                "; border-radius: 6px; padding: 12px; max-height: 460px; overflow-y: auto;'>", unsafe_allow_html=True)

    for _, row in month_scores.head(20).iterrows():
        risk = row["risk_score"]
        if risk >= 80:
            badge_class = "critical"
            badge_text = "CRIT"
        elif risk >= 65:
            badge_class = "high"
            badge_text = "HIGH"
        else:
            badge_class = "mod"
            badge_text = "MOD"

        city_a = city_lookup.get(row['airport_a'], row['airport_a'])
        city_b = city_lookup.get(row['airport_b'], row['airport_b'])

        st.markdown(f"""
        <div class="feed-row">
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <span class="pair-label">{row['airport_a']} ↔ {row['airport_b']}</span>
                    <span class="risk-badge {badge_class}">{badge_text} · {risk:.0f}</span>
                </div>
            </div>
            <div style='color: {C['muted']}; font-size: 11px; margin-top: 2px;'>
                {city_a}  ·  {city_b}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# =========================================================================
# SECOND ROW: Seasonal Heatmap + Baseline Comparison
# =========================================================================
heat_col, base_col = st.columns([1.3, 1])

with heat_col:
    st.markdown(f"<p class='panel-title'>SEASONAL RISK MATRIX · TOP 15 PAIRS</p>", unsafe_allow_html=True)

    pair_avg = risk_scores.groupby(["airport_a", "airport_b"])["risk_score"].mean().nlargest(15)
    top_pairs_list = pair_avg.index.tolist()
    mask = risk_scores.apply(lambda r: (r["airport_a"], r["airport_b"]) in top_pairs_list, axis=1)
    hm = risk_scores[mask].copy()
    hm["pair"] = hm["airport_a"] + "–" + hm["airport_b"]
    labels = [f"{a}–{b}" for a, b in top_pairs_list]
    pivot = hm.pivot_table(values="risk_score", index="pair", columns="month", aggfunc="mean").reindex(labels)

    fig_hm = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=MONTH_NAMES,
        y=pivot.index,
        colorscale=[[0, C["panel"]], [0.3, C["teal"]], [0.6, C["gold"]], [1.0, C["coral"]]],
        colorbar=dict(
            title=dict(text="Risk", font=dict(color=C["ice"])),
            tickfont=dict(color=C["ice"]),
            thickness=10,
            len=0.8,
        ),
        hovertemplate="%{y} · %{x}<br>Risk: %{z:.0f}<extra></extra>",
    ))
    fig_hm.update_layout(
        height=340,
        margin=dict(l=80, r=10, t=10, b=30),
        paper_bgcolor=C["bg"],
        plot_bgcolor=C["bg"],
        xaxis=dict(tickfont=dict(color=C["ice"], size=10), showgrid=False),
        yaxis=dict(tickfont=dict(color=C["ice"], family="Consolas", size=10), showgrid=False),
    )
    st.plotly_chart(fig_hm, use_container_width=True)

with base_col:
    st.markdown(f"<p class='panel-title'>MODEL vs. NAIVE BASELINE</p>", unsafe_allow_html=True)

    if baseline is not None:
        fig_b = go.Figure()
        fig_b.add_trace(go.Bar(
            name="StormChain",
            x=[f"K={int(k)}" for k in baseline["k"]],
            y=baseline["our_minutes_caught"] / 1000,
            marker_color=C["coral"],
            text=[f"+{v:.0f}%" for v in baseline["improvement_pct"]],
            textposition="outside",
            textfont=dict(color=C["gold"], size=12),
        ))
        fig_b.add_trace(go.Bar(
            name="Naive",
            x=[f"K={int(k)}" for k in baseline["k"]],
            y=baseline["naive_minutes_caught"] / 1000,
            marker_color=C["muted"],
        ))
        fig_b.update_layout(
            barmode="group",
            height=340,
            margin=dict(l=40, r=10, t=10, b=30),
            paper_bgcolor=C["bg"],
            plot_bgcolor=C["bg"],
            xaxis=dict(tickfont=dict(color=C["ice"]), showgrid=False),
            yaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"],
                       title=dict(text="Cascade Minutes Caught (K)", font=dict(color=C["ice"], size=11))),
            legend=dict(font=dict(color=C["ice"]), orientation="h", y=1.1),
        )
        st.plotly_chart(fig_b, use_container_width=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# =========================================================================
# CASE STUDY STRIP
# =========================================================================
if case_study is not None:
    st.markdown(f"""
    <p class='panel-title'>
        INCIDENT LOG · MAY 28, 2024 · WORST CASCADE DAY
    </p>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown(f"""
        <div class="ops-panel">
            <p style='color: {C['gold']}; font-size: 11px; letter-spacing: 2px; margin-bottom: 12px;'>
                METAR 05:53 UTC
            </p>
            <p style='font-family: Consolas, monospace; color: {C['coral']}; font-size: 18px; margin-bottom: 12px;'>
                +TSRA FG SQ
            </p>
            <p style='color: {C['ice']}; font-size: 13px; margin-bottom: 16px;'>
                Heavy thunderstorm, fog, squall. Zero visibility at DFW.
            </p>
            <div style='display: flex; justify-content: space-between; padding-top: 12px; border-top: 1px solid {C['border']};'>
                <div>
                    <p style='color: {C['muted']}; font-size: 10px; letter-spacing: 2px; margin: 0;'>SEQUENCES</p>
                    <p style='color: {C['white']}; font-family: Georgia; font-size: 22px; font-weight: bold; margin: 0;'>170</p>
                </div>
                <div>
                    <p style='color: {C['muted']}; font-size: 10px; letter-spacing: 2px; margin: 0;'>PROPAGATED</p>
                    <p style='color: {C['coral']}; font-family: Georgia; font-size: 22px; font-weight: bold; margin: 0;'>149</p>
                </div>
                <div>
                    <p style='color: {C['muted']}; font-size: 10px; letter-spacing: 2px; margin: 0;'>COST</p>
                    <p style='color: {C['gold']}; font-family: Georgia; font-size: 22px; font-weight: bold; margin: 0;'>$4.4M</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        case_study["arr_hour"] = (case_study["inbound_arr_time"] // 60).astype(int)
        hourly = case_study.groupby("arr_hour")["total_cascade_minutes"].sum().reindex(range(6, 22), fill_value=0)

        fig_cs = go.Figure()
        colors_bar = [C["coral"] if v == hourly.max() or v == hourly.nlargest(2).iloc[-1] else C["gold"]
                      for v in hourly.values]
        fig_cs.add_trace(go.Bar(
            x=[f"{h:02d}:00" for h in hourly.index],
            y=hourly.values,
            marker_color=colors_bar,
            hovertemplate="%{x}<br>%{y:,.0f} cascade min<extra></extra>",
        ))
        fig_cs.update_layout(
            height=220,
            margin=dict(l=40, r=10, t=10, b=30),
            paper_bgcolor=C["panel"],
            plot_bgcolor=C["panel"],
            xaxis=dict(tickfont=dict(color=C["ice"], size=10), showgrid=False),
            yaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"],
                       title=dict(text="Cascade Minutes", font=dict(color=C["ice"], size=11))),
        )
        st.plotly_chart(fig_cs, use_container_width=True)
        st.markdown(f"""
        <p style='color: {C['muted']}; font-size: 11px; text-align: center; margin-top: -8px;'>
            Morning wave (07:00–09:00) concentrated ~70% of cascade damage as overnight delays propagated.
        </p>
        """, unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# =========================================================================
# DEEP ANALYSIS (collapsible)
# =========================================================================
st.markdown(f"<p class='panel-title'>DEEP ANALYSIS · EXPAND FOR DETAIL</p>", unsafe_allow_html=True)

with st.expander("▸ PAIR EXPLORER · Investigate specific airport pairs", expanded=False):
    exp_col1, exp_col2 = st.columns(2)
    all_aps = sorted(set(risk_scores["airport_a"]) | set(risk_scores["airport_b"]))
    with exp_col1:
        airport_a = st.selectbox("Airport A", all_aps, key="pair_a")
    with exp_col2:
        airport_b = st.selectbox("Airport B", all_aps,
                                  index=min(1, len(all_aps) - 1), key="pair_b")

    pair_data = risk_scores[
        ((risk_scores["airport_a"] == airport_a) & (risk_scores["airport_b"] == airport_b)) |
        ((risk_scores["airport_a"] == airport_b) & (risk_scores["airport_b"] == airport_a))
    ].sort_values("month")

    if len(pair_data) > 0:
        fig_pair = go.Figure()
        fig_pair.add_trace(go.Bar(
            x=MONTH_NAMES,
            y=pair_data["risk_score"],
            marker_color=[C["coral"] if r >= 80 else C["gold"] if r >= 65 else C["teal"]
                          for r in pair_data["risk_score"]],
        ))
        fig_pair.update_layout(
            height=240,
            title=dict(text=f"Monthly Risk: {airport_a} ↔ {airport_b}",
                       font=dict(color=C["white"], family="Georgia")),
            margin=dict(l=40, r=10, t=40, b=20),
            paper_bgcolor=C["panel"],
            plot_bgcolor=C["panel"],
            xaxis=dict(tickfont=dict(color=C["ice"]), showgrid=False),
            yaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"],
                       range=[0, 100]),
        )
        st.plotly_chart(fig_pair, use_container_width=True)

        mcols = st.columns(4)
        mcols[0].metric("Average Risk", f"{pair_data['risk_score'].mean():.1f}")
        mcols[1].metric("Peak Risk", f"{pair_data['risk_score'].max():.1f}")
        mcols[2].metric("Peak Month", MONTH_NAMES[pair_data.loc[pair_data["risk_score"].idxmax(), "month"]-1])
        mcols[3].metric("Joint Weather Prob", f"{pair_data['joint_weather_delay_prob'].mean():.3f}")

with st.expander("▸ AVOID LIST · Full pair-season recommendations", expanded=False):
    if avoid_list is not None:
        season_filter = st.selectbox(
            "Season",
            ["All"] + sorted(avoid_list["season"].unique()),
            key="avoid_season",
        )
        display = avoid_list if season_filter == "All" else avoid_list[avoid_list["season"] == season_filter]
        st.dataframe(
            display[["season", "airport_a", "airport_b", "risk_score", "reason"]].head(100),
            use_container_width=True,
            height=400,
        )
        st.caption(f"Showing {min(100, len(display))} of {len(display)} recommendations")

with st.expander("▸ SWAP RECOMMENDATIONS · Safe alternatives for flagged pairs", expanded=False):
    if swap_recs is not None:
        st.dataframe(
            swap_recs[["season", "avoid_origin", "avoid_dest", "avoid_risk",
                       "swap_dest", "swap_risk", "risk_reduction"]].head(50),
            use_container_width=True, height=400,
        )
        st.caption(f"Avg risk reduction per swap: {swap_recs['risk_reduction'].mean():.0f} points")

with st.expander("▸ MODEL INTERNALS · XGBoost ROC, PR, and feature importance", expanded=False):
    # Model metrics summary
    mm_cols = st.columns(4)
    mm_cols[0].metric("AUC-ROC", "0.81")
    mm_cols[1].metric("AUC-PR", "0.12")
    mm_cols[2].metric("Recall", "66%")
    mm_cols[3].metric("Features", "117")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ROC and PR curves side by side
    curve_c1, curve_c2 = st.columns(2)
    with curve_c1:
        if roc_curve is not None:
            fig_roc = go.Figure()
            fig_roc.add_trace(go.Scatter(
                x=roc_curve["fpr"], y=roc_curve["tpr"],
                mode="lines", fill="tozeroy",
                line=dict(color=C["coral"], width=2),
                fillcolor=f"rgba(255, 107, 107, 0.15)",
                name="StormChain",
            ))
            fig_roc.add_trace(go.Scatter(
                x=[0, 1], y=[0, 1],
                mode="lines", line=dict(color=C["muted"], width=1, dash="dash"),
                name="Random",
            ))
            fig_roc.update_layout(
                height=320,
                title=dict(text="ROC Curve (AUC 0.81)", font=dict(color=C["white"], family="Georgia", size=14)),
                margin=dict(l=50, r=10, t=40, b=40),
                paper_bgcolor=C["panel"],
                plot_bgcolor=C["panel"],
                xaxis=dict(title=dict(text="False Positive Rate", font=dict(color=C["ice"])),
                           tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
                yaxis=dict(title=dict(text="True Positive Rate", font=dict(color=C["ice"])),
                           tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
                showlegend=False,
            )
            st.plotly_chart(fig_roc, use_container_width=True)

    with curve_c2:
        if pr_curve is not None:
            fig_pr = go.Figure()
            fig_pr.add_trace(go.Scatter(
                x=pr_curve["recall"], y=pr_curve["precision"],
                mode="lines", fill="tozeroy",
                line=dict(color=C["gold"], width=2),
                fillcolor=f"rgba(249, 178, 51, 0.15)",
                name="StormChain",
            ))
            fig_pr.update_layout(
                height=320,
                title=dict(text="Precision-Recall Curve (AUC 0.12)", font=dict(color=C["white"], family="Georgia", size=14)),
                margin=dict(l=50, r=10, t=40, b=40),
                paper_bgcolor=C["panel"],
                plot_bgcolor=C["panel"],
                xaxis=dict(title=dict(text="Recall", font=dict(color=C["ice"])),
                           tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
                yaxis=dict(title=dict(text="Precision", font=dict(color=C["ice"])),
                           tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
                showlegend=False,
            )
            st.plotly_chart(fig_pr, use_container_width=True)

    st.caption(
        "Low AUC-PR is expected — only 2.5% of sequences are cascading delays. "
        "The XGBoost model's primary value is feature importance (below), not per-flight prediction. "
        "The risk scoring model handles sparsity by aggregating to monthly pair-level statistics."
    )

    # Feature importance
    if importance is not None:
        top_imp = importance.head(15).iloc[::-1]
        fig_imp = go.Figure()
        fig_imp.add_trace(go.Bar(
            x=top_imp["importance"],
            y=top_imp["feature"],
            orientation="h",
            marker_color=[C["coral"] if f.startswith("wx_dfw") else C["deep_blue"]
                          for f in top_imp["feature"]],
        ))
        fig_imp.update_layout(
            height=400,
            title=dict(text="Top 15 Features by Gain", font=dict(color=C["white"], family="Georgia")),
            margin=dict(l=200, r=10, t=40, b=30),
            paper_bgcolor=C["panel"],
            plot_bgcolor=C["panel"],
            xaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
            yaxis=dict(tickfont=dict(color=C["ice"], family="Consolas", size=10)),
        )
        st.plotly_chart(fig_imp, use_container_width=True)
        st.caption("Coral bars = DFW hub weather features. Blue = other features.")

with st.expander("▸ IMPACT ANALYSIS · Simulation results and dollar estimates", expanded=False):
    if sim_results is not None:
        imp_c1, imp_c2 = st.columns(2)
        with imp_c1:
            fig_sav = go.Figure()
            fig_sav.add_trace(go.Scatter(
                x=sim_results["k"],
                y=sim_results["dollar_savings"] / 1e6,
                mode="lines+markers",
                line=dict(color=C["coral"], width=3),
                marker=dict(size=10, color=C["gold"]),
                name="Upper bound",
            ))
            fig_sav.update_layout(
                height=320,
                title=dict(text="Total Savings by Pairs Avoided (5-year)",
                           font=dict(color=C["white"], family="Georgia", size=14)),
                margin=dict(l=50, r=10, t=40, b=40),
                paper_bgcolor=C["panel"],
                plot_bgcolor=C["panel"],
                xaxis=dict(title=dict(text="K Pairs Avoided", font=dict(color=C["ice"])),
                           tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
                yaxis=dict(title=dict(text="Savings ($M)", font=dict(color=C["ice"])),
                           tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
            )
            st.plotly_chart(fig_sav, use_container_width=True)

        with imp_c2:
            fig_pct = go.Figure()
            fig_pct.add_trace(go.Bar(
                x=[f"K={int(k)}" for k in sim_results["k"]],
                y=sim_results["pct_events_prevented"],
                marker_color=[C["teal"], C["gold"], C["coral"], C["coral"]],
                text=[f"{v:.1f}%" for v in sim_results["pct_events_prevented"]],
                textposition="outside",
                textfont=dict(color=C["white"]),
            ))
            fig_pct.update_layout(
                height=320,
                title=dict(text="% of Cascading Events Prevented",
                           font=dict(color=C["white"], family="Georgia", size=14)),
                margin=dict(l=50, r=10, t=40, b=40),
                paper_bgcolor=C["panel"],
                plot_bgcolor=C["panel"],
                xaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
                yaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
            )
            st.plotly_chart(fig_pct, use_container_width=True)

        # Full breakdown table
        display = sim_results.copy()
        display["Dollar Savings (5yr)"] = display["dollar_savings"].apply(lambda x: f"${x/1e6:.1f}M")
        if "adjusted_savings" in display.columns:
            display["Adjusted (5yr)"] = display["adjusted_savings"].apply(lambda x: f"${x/1e3:.0f}K")
        display["% Events Prevented"] = display["pct_events_prevented"].apply(lambda x: f"{x:.2f}%")
        display["Events Prevented"] = display["prevented_events"].apply(lambda x: f"{int(x):,}")
        display["K"] = display["k"].astype(int)

        cols_to_show = ["K", "Events Prevented", "% Events Prevented", "Dollar Savings (5yr)"]
        if "Adjusted (5yr)" in display.columns:
            cols_to_show.append("Adjusted (5yr)")
        st.dataframe(display[cols_to_show], use_container_width=True, hide_index=True)

        st.caption(
            "Upper bound assumes every flagged pair was assigned every impacted day. "
            "Adjusted estimate scales by assignment probability (~1.3%). "
            "Realistic savings fall between these bounds; targeted scheduling pushes toward the upper bound."
        )

        # Monthly breakdown if available
        if monthly_breakdown is not None:
            best_k = int(sim_results["k"].max())
            mb = monthly_breakdown[monthly_breakdown["k"] == best_k].copy()
            month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            mb["month_name"] = mb["month"].apply(lambda m: month_names[m-1])

            fig_mo = go.Figure()
            fig_mo.add_trace(go.Bar(
                x=mb["month_name"],
                y=mb["dollar_savings"] / 1e6,
                marker_color=[C["coral"] if v > mb["dollar_savings"].quantile(0.7)/1e6
                              else C["gold"] if v > mb["dollar_savings"].quantile(0.4)/1e6
                              else C["teal"]
                              for v in mb["dollar_savings"] / 1e6],
            ))
            fig_mo.update_layout(
                height=260,
                title=dict(text=f"Monthly Savings Breakdown (K={best_k}, 5-year totals)",
                           font=dict(color=C["white"], family="Georgia", size=13)),
                margin=dict(l=50, r=10, t=40, b=30),
                paper_bgcolor=C["panel"],
                plot_bgcolor=C["panel"],
                xaxis=dict(tickfont=dict(color=C["ice"]), showgrid=False),
                yaxis=dict(title=dict(text="Savings ($M)", font=dict(color=C["ice"])),
                           tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
            )
            st.plotly_chart(fig_mo, use_container_width=True)

with st.expander("▸ SEASONAL PATTERNS · Top pairs by season with geographic patterns", expanded=False):
    if seasonal_summary is not None:
        for season in seasonal_summary["season"].unique():
            st.markdown(f"<p style='color: {C['gold']}; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; font-size: 13px; margin-top: 12px;'>{season}</p>", unsafe_allow_html=True)
            season_data = seasonal_summary[seasonal_summary["season"] == season]
            st.dataframe(
                season_data[["rank", "airport_a", "airport_b", "avg_risk", "geographic_pattern"]],
                use_container_width=True, hide_index=True,
            )

with st.expander("▸ CASE STUDY DETAIL · May 28, 2024 — top cascading pairs", expanded=False):
    if case_study is not None:
        case_pair_summary = case_study.groupby(["origin", "dest"]).agg(
            sequences=("total_cascade_minutes", "size"),
            total_cascade=("total_cascade_minutes", "sum"),
            avg_cascade=("total_cascade_minutes", "mean"),
            risk_score=("risk_score", "mean"),
        ).sort_values("total_cascade", ascending=False).head(20).reset_index()
        case_pair_summary["total_cascade"] = case_pair_summary["total_cascade"].round(0).astype(int)
        case_pair_summary["avg_cascade"] = case_pair_summary["avg_cascade"].round(0).astype(int)
        case_pair_summary["risk_score"] = case_pair_summary["risk_score"].round(1)
        case_pair_summary.columns = ["Origin", "Dest", "Sequences", "Total Cascade (min)", "Avg Cascade (min)", "Model Risk Score"]
        st.dataframe(case_pair_summary, use_container_width=True, hide_index=True)

        st.caption(
            "Many top cascading routes have low or zero model risk scores — extreme weather events produce "
            "cascades on unusual route combinations that monthly aggregation cannot predict. "
            "StormChain's strength is recurring seasonal patterns, not one-off extreme events."
        )

    if top_cascading_pairs is not None:
        st.markdown(f"<p style='color: {C['gold']}; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; font-size: 13px; margin-top: 20px;'>ALL-TIME TOP 20 CASCADING PAIRS (2019–2024)</p>", unsafe_allow_html=True)
        tp = top_cascading_pairs.head(20).copy()
        tp["total_delay_minutes"] = tp["total_delay_minutes"].round(0).astype(int)
        tp["avg_delay"] = tp["avg_delay"].round(1)
        tp.columns = ["Pair A", "Pair B", "Total Events", "Total Delay (min)", "Avg Delay (min)"]
        st.dataframe(tp, use_container_width=True, hide_index=True)

# =========================================================================
# FOOTER
# =========================================================================
st.markdown(f"""
<div style='margin-top: 32px; padding: 16px 0; border-top: 1px solid {C['border']};
            text-align: center; color: {C['muted']}; font-size: 11px; letter-spacing: 2px;'>
    STORMCHAIN · EPPS-AMERICAN AIRLINES DATA CHALLENGE GROW 26.2 · drPod<br>
    <span style='color: {C['ice']};'>
        github.com/drPod/stormchain
    </span>
</div>
""", unsafe_allow_html=True)
