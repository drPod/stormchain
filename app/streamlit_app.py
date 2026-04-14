"""StormChain Operations Command Center — tactical dashboard for crew sequence risk."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
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

    /* Narrative section styles */
    .section-kicker {{
        display: inline-block;
        font-family: 'Consolas', monospace;
        font-size: 11px;
        letter-spacing: 4px;
        color: {C['coral']};
        padding: 4px 10px;
        border: 1px solid {C['coral']};
        border-radius: 2px;
        margin-bottom: 16px;
    }}
    .section-title {{
        font-family: 'Georgia', serif;
        font-size: 32px;
        font-weight: bold;
        color: {C['white']};
        line-height: 1.2;
        margin-bottom: 8px;
    }}
    .section-subtitle {{
        font-size: 16px;
        color: {C['ice']};
        font-style: italic;
        margin-bottom: 24px;
        max-width: 900px;
    }}
    .section-divider {{
        border: none;
        border-top: 1px solid {C['border']};
        margin: 48px 0 32px 0;
    }}
    .code-comment {{
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 13px;
        color: {C['muted']};
        background: transparent;
        padding: 8px 0 16px 4px;
        line-height: 1.6;
        border-left: 2px solid {C['border']};
        padding-left: 16px;
        margin-top: 8px;
        margin-bottom: 24px;
    }}
    .code-comment strong {{
        color: {C['gold']};
        font-weight: 600;
    }}
    .code-comment .insight {{
        color: {C['coral']};
        font-weight: 600;
    }}

    /* Opening hook */
    .hook {{
        padding: 60px 0 80px 0;
        border-bottom: 1px solid {C['border']};
        margin-bottom: 48px;
    }}
    .hook-timestamp {{
        font-family: 'Consolas', monospace;
        font-size: 13px;
        letter-spacing: 4px;
        color: {C['gold']};
        margin-bottom: 24px;
    }}
    .hook-metar {{
        font-family: 'Consolas', monospace;
        font-size: 72px;
        font-weight: bold;
        color: {C['coral']};
        letter-spacing: 4px;
        line-height: 1;
        margin-bottom: 16px;
    }}
    .hook-metar-desc {{
        font-family: 'Georgia', serif;
        font-style: italic;
        font-size: 20px;
        color: {C['ice']};
        margin-bottom: 48px;
    }}
    .hook-narrative {{
        font-family: 'Georgia', serif;
        font-size: 28px;
        color: {C['white']};
        line-height: 1.5;
        max-width: 950px;
        margin-bottom: 32px;
    }}
    .hook-stats {{
        display: flex;
        gap: 40px;
        margin: 32px 0 48px 0;
    }}
    .hook-stat {{
        border-left: 2px solid {C['coral']};
        padding-left: 16px;
    }}
    .hook-stat-value {{
        font-family: 'Georgia', serif;
        font-size: 48px;
        font-weight: bold;
        color: {C['white']};
        line-height: 1;
    }}
    .hook-stat-label {{
        font-size: 12px;
        color: {C['muted']};
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 4px;
    }}
    .hook-mission {{
        font-family: 'Georgia', serif;
        font-size: 32px;
        color: {C['gold']};
        line-height: 1.3;
        margin-top: 32px;
        max-width: 900px;
    }}
    .scroll-hint {{
        margin-top: 40px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        letter-spacing: 3px;
        color: {C['muted']};
    }}
    .scroll-hint .arrow {{
        display: inline-block;
        animation: bounce 2s infinite;
        color: {C['coral']};
        font-size: 18px;
        margin-left: 8px;
    }}
    @keyframes bounce {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(6px); }}
    }}

    /* Closing section */
    .closing {{
        padding: 60px 0 40px 0;
        margin-top: 60px;
        border-top: 1px solid {C['border']};
    }}
    .closing-kicker {{
        display: inline-block;
        font-family: 'Consolas', monospace;
        font-size: 11px;
        letter-spacing: 4px;
        color: {C['green']};
        padding: 4px 10px;
        border: 1px solid {C['green']};
        border-radius: 2px;
        margin-bottom: 24px;
    }}
    .closing-title {{
        font-family: 'Georgia', serif;
        font-size: 44px;
        font-weight: bold;
        color: {C['white']};
        line-height: 1.2;
        margin-bottom: 20px;
        max-width: 1000px;
    }}
    .closing-tagline {{
        font-family: 'Georgia', serif;
        font-size: 22px;
        font-style: italic;
        color: {C['ice']};
        margin-bottom: 32px;
        max-width: 900px;
    }}
    .closing-ascii {{
        font-family: 'Consolas', monospace;
        background: {C['panel']};
        border: 1px solid {C['border']};
        border-left: 3px solid {C['green']};
        padding: 20px 24px;
        font-size: 14px;
        color: {C['ice']};
        line-height: 1.8;
        margin: 32px 0;
        max-width: 700px;
    }}
    .closing-ascii .line-ok {{ color: {C['green']}; }}
    .closing-ascii .line-info {{ color: {C['gold']}; }}
    .closing-cta {{
        margin-top: 40px;
        padding: 20px 0;
        border-top: 1px solid {C['border']};
        font-size: 14px;
        color: {C['muted']};
    }}
    .closing-cta a {{
        color: {C['coral']};
        text-decoration: none;
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
# NARRATIVE HELPERS
# =========================================================================
def section_header(kicker: str, title: str, subtitle: str = ""):
    """Render a section header with kicker, title, and subtitle."""
    html = f"""
    <hr class="section-divider" />
    <div style='margin-bottom: 24px;'>
        <span class="section-kicker">{kicker}</span>
        <h2 class="section-title">{title}</h2>
    """
    if subtitle:
        html += f'<p class="section-subtitle">{subtitle}</p>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def comment(*lines: str):
    """Render code-comment-style annotations below a chart."""
    body = "<br>".join(f"<span style='color: {C['muted']};'>//</span> {line}" for line in lines)
    st.markdown(f"<div class='code-comment'>{body}</div>", unsafe_allow_html=True)


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


@st.cache_data(ttl=300)
def fetch_live_metar(stations: tuple = ("KDFW", "KORD", "KATL", "KMCO", "KLGA", "KLAX")):
    """Fetch current METAR for key airports from Aviation Weather Center.
    Cached 5 min — genuinely live within that window."""
    try:
        url = "https://aviationweather.gov/api/data/metar"
        ids = ",".join(stations)
        resp = requests.get(url, params={"ids": ids, "format": "json"}, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for obs in data:
            icao = obs.get("icaoId", "")
            ceiling = 99999
            for c in (obs.get("clouds") or []):
                if c.get("cover") in ("BKN", "OVC") and c.get("base"):
                    ceiling = min(ceiling, c["base"])
            vis_raw = obs.get("visib", "10")
            try:
                vis = float(str(vis_raw).replace("+", ""))
            except (ValueError, TypeError):
                vis = 10
            if ceiling < 500 or vis < 1:
                cat = "LIFR"
            elif ceiling < 1000 or vis < 3:
                cat = "IFR"
            elif ceiling < 3000 or vis < 5:
                cat = "MVFR"
            else:
                cat = "VFR"
            results.append({
                "icao": icao,
                "iata": icao[1:] if icao.startswith("K") else icao,
                "temp_c": obs.get("temp"),
                "dewp_c": obs.get("dewp"),
                "wind_dir": obs.get("wdir"),
                "wind_kt": obs.get("wspd"),
                "gust_kt": obs.get("wgst"),
                "vis_sm": vis,
                "ceiling_ft": ceiling if ceiling < 99999 else None,
                "raw": obs.get("rawOb", ""),
                "category": cat,
                "report_time": obs.get("reportTime"),
            })
        return pd.DataFrame(results)
    except Exception:
        return pd.DataFrame()


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
# OPENING HOOK — the problem statement before the tool
# =========================================================================
_hook_html = (
    '<div class="hook">'
    '<div class="hook-timestamp">TRANSCRIPT · MAY 28, 2024 · 05:53 UTC · DFW METAR</div>'
    '<div class="hook-metar">+TSRA FG SQ</div>'
    '<div class="hook-metar-desc">Heavy thunderstorm. Fog. Squall. Zero visibility.</div>'
    '<div class="hook-narrative">'
    f'<strong style="color: {C["white"]};">What followed destroyed the day\'s schedule.</strong><br>'
    'One weather system. One hub. A pilot caught on a flight from MCO arrived at DFW late, '
    'their outbound to MIA cascaded, their passengers missed connections — '
    'and the chain reaction spread through the network for 16 hours.'
    '</div>'
    '<div class="hook-stats">'
    '<div class="hook-stat"><div class="hook-stat-value">172</div><div class="hook-stat-label">inbound delayed</div></div>'
    '<div class="hook-stat"><div class="hook-stat-value">471</div><div class="hook-stat-label">outbound cascaded</div></div>'
    '<div class="hook-stat"><div class="hook-stat-value">$4.4M</div><div class="hook-stat-label">cost, one day</div></div>'
    '</div>'
    '<div class="hook-mission">StormChain was built to prevent the next one.</div>'
    '<div class="scroll-hint">SCROLL TO INVESTIGATE <span class="arrow">▼</span></div>'
    '</div>'
)
st.markdown(_hook_html, unsafe_allow_html=True)

# =========================================================================
# § 01 — THE TOOL (operations command center)
# =========================================================================
section_header(
    "§ 01 / THE TOOL",
    "A real-time view of crew sequence risk through DFW",
    "Every metric below updates with the month selector. The radar shows the top-K riskiest pairs for that month. "
    "The risk feed lists them with city names and severity. Pick a month to see how the pattern shifts.",
)

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
# LIVE METAR STRIP — real current conditions from AWC API (5-min cache)
# =========================================================================
live_metar = fetch_live_metar()
if len(live_metar) > 0:
    cat_colors = {
        "VFR": C["green"], "MVFR": C["gold"],
        "IFR": C["coral"], "LIFR": C["coral"],
    }
    tiles_html = ""
    for _, r in live_metar.iterrows():
        cat = r["category"]
        color = cat_colors.get(cat, C["muted"])
        def safe_int(v):
            try:
                if v is None or pd.isna(v):
                    return None
                return int(v)
            except (ValueError, TypeError):
                return None

        wind_kt = safe_int(r.get("wind_kt"))
        gust_kt = safe_int(r.get("gust_kt"))
        ceiling = safe_int(r.get("ceiling_ft"))
        vis = r.get("vis_sm", 10) or 10

        wind_str = f"{wind_kt}kt" if wind_kt is not None else "—"
        if gust_kt:
            wind_str += f" G{gust_kt}"
        ceiling_str = f"{ceiling}ft" if ceiling else "—"
        vis_str = f"{vis:.0f}SM" if vis >= 1 else f"{vis:.1f}SM"

        tiles_html += (
            f'<div style="flex: 1; background: {C["panel"]}; border: 1px solid {C["border"]}; '
            f'border-top: 3px solid {color}; padding: 10px 14px; min-width: 0;">'
            f'<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">'
            f'<span style="font-family: Consolas, monospace; font-size: 16px; font-weight: bold; color: {C["white"]};">{r["iata"]}</span>'
            f'<span style="font-family: Consolas, monospace; font-size: 10px; font-weight: bold; color: {color}; letter-spacing: 1px;">{cat}</span>'
            f'</div>'
            f'<div style="font-size: 10px; color: {C["muted"]}; line-height: 1.5;">'
            f'WIND {wind_str}<br>VIS {vis_str}<br>CIG {ceiling_str}'
            f'</div>'
            f'</div>'
        )

    # Timestamp of latest obs
    report_times = [r for r in live_metar["report_time"] if r]
    latest = max(report_times) if report_times else ""

    live_html = (
        f'<div style="margin: 12px 0 16px 0;">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">'
        f'<span style="font-family: Consolas, monospace; font-size: 11px; letter-spacing: 3px; color: {C["coral"]};">'
        f'<span class="status-dot"></span>LIVE CONDITIONS · FETCHED FROM AWC METAR API'
        f'</span>'
        f'<span style="font-family: Consolas, monospace; font-size: 10px; color: {C["muted"]};">'
        f'LAST OBS {latest[11:16] if latest else "—"}Z · CACHE 5 MIN'
        f'</span>'
        f'</div>'
        f'<div style="display: flex; gap: 8px;">{tiles_html}</div>'
        f'</div>'
    )
    st.markdown(live_html, unsafe_allow_html=True)

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
        TOP PAIRS · WITH SWAP
    </p>
    <p style='font-size: 11px; color: {C['muted']}; margin-top: 0; margin-bottom: 12px;'>
        Top 5 pairs for this month — each with a safer alternative destination
    </p>
    """, unsafe_allow_html=True)

    # Airport city lookup
    city_lookup = airports.set_index("iata")["city"].to_dict()

    # Build per-pair swap lookup for the selected month
    active_dests = set(risk_scores["airport_b"]).union(set(risk_scores["airport_a"]))

    def find_swap(origin, avoid_dest, month):
        """Find a safer alternative outbound destination for a given origin in this month."""
        candidates = risk_scores[
            (risk_scores["month"] == month) &
            ((risk_scores["airport_a"] == origin) | (risk_scores["airport_b"] == origin))
        ].copy()
        if candidates.empty:
            return None
        candidates["other"] = np.where(
            candidates["airport_a"] == origin,
            candidates["airport_b"], candidates["airport_a"]
        )
        candidates = candidates[(candidates["other"] != avoid_dest) & (candidates["risk_score"] < 30)]
        if candidates.empty:
            return None
        best = candidates.nsmallest(1, "risk_score").iloc[0]
        return {"dest": best["other"], "risk": best["risk_score"]}

    rows_html = ""
    for _, row in month_scores.head(5).iterrows():
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

        # Find a swap alternative for the A→DFW→B direction
        swap = find_swap(row['airport_a'], row['airport_b'], selected_month)
        swap_html = ""
        if swap:
            swap_city = city_lookup.get(swap['dest'], swap['dest'])
            swap_html = (
                f'<div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed {C["border"]};">'
                f'<div style="font-size: 10px; color: {C["muted"]}; letter-spacing: 2px;">'
                f'<span style="color: {C["gold"]};">→ SWAP</span> '
                f'{row["airport_a"]} → DFW → <span style="color: {C["green"]};">{swap["dest"]}</span> '
                f'<span style="color: {C["green"]}; font-weight: bold;">risk {swap["risk"]:.0f}</span>'
                f'</div>'
                f'<div style="font-size: 10px; color: {C["muted"]}; margin-top: 2px;">'
                f'safer alternative: {swap_city}'
                f'</div>'
                f'</div>'
            )

        rows_html += (
            f'<div class="feed-row">'
            f'<div style="display: flex; justify-content: space-between; align-items: center;">'
            f'<span class="pair-label">{row["airport_a"]} ↔ {row["airport_b"]}</span>'
            f'<span class="risk-badge {badge_class}">{badge_text} · {risk:.0f}</span>'
            f'</div>'
            f'<div style="color: {C["muted"]}; font-size: 11px; margin-top: 2px;">'
            f'{city_a} · {city_b}'
            f'</div>'
            f'{swap_html}'
            f'</div>'
        )

    st.markdown(rows_html, unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# =========================================================================
# § 02 — SEASONAL INTELLIGENCE
# =========================================================================
section_header(
    "§ 02 / PATTERNS",
    "Weather risk isn't random — it follows the calendar",
    "Spring thunderstorms in the Southeast, Florida afternoon convection in summer, "
    "Northeast snowstorms in winter. The months when pairs get dangerous are highly predictable.",
)

pair_avg = risk_scores.groupby(["airport_a", "airport_b"])["risk_score"].mean().nlargest(15)
top_pairs_list = pair_avg.index.tolist()
mask = risk_scores.apply(lambda r: (r["airport_a"], r["airport_b"]) in top_pairs_list, axis=1)
hm = risk_scores[mask].copy()
hm["pair"] = hm["airport_a"] + "–" + hm["airport_b"]
labels = [f"{a}–{b}" for a, b in top_pairs_list]
pivot = hm.pivot_table(values="risk_score", index="pair", columns="month", aggfunc="mean").reindex(labels)

fig_hm = go.Figure(data=go.Heatmap(
    z=pivot.values, x=MONTH_NAMES, y=pivot.index,
    colorscale=[[0, C["panel"]], [0.3, C["teal"]], [0.6, C["gold"]], [1.0, C["coral"]]],
    colorbar=dict(
        title=dict(text="Risk", font=dict(color=C["ice"])),
        tickfont=dict(color=C["ice"]),
        thickness=10, len=0.8,
    ),
    hovertemplate="%{y} · %{x}<br>Risk: %{z:.0f}<extra></extra>",
))
fig_hm.update_layout(
    height=420,
    margin=dict(l=90, r=10, t=10, b=30),
    paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
    xaxis=dict(tickfont=dict(color=C["ice"], size=11), showgrid=False),
    yaxis=dict(tickfont=dict(color=C["ice"], family="Consolas", size=10), showgrid=False),
)
st.plotly_chart(fig_hm, use_container_width=True)

comment(
    "Top 15 pairs, averaged across 5 years of data",
    "<strong>May-June is the epicenter</strong> — spring thunderstorms peaking in Southeast/South-Central corridors",
    "Summer shifts focus to MCO — Orlando's afternoon convection hits outbound sequences hard",
    "<span class='insight'>→ Winter is calmer overall, but specific Pacific/Northeast pairs spike (LAX-SAN Santa Ana winds, ORD-LGA snowstorms)</span>",
)


# =========================================================================
# § 03 — MODEL VALIDATION
# =========================================================================
section_header(
    "§ 03 / THE PROOF",
    "Beating the naive baseline by 78%",
    "The dumbest possible approach: flag pairs where both airports individually have above-median weather delays. "
    "StormChain catches dramatically more actual cascading delays — because it captures correlated weather, "
    "tight turnarounds, and cascade mechanics the naive approach can't see.",
)

if baseline is not None:
    fig_b = go.Figure()
    fig_b.add_trace(go.Bar(
        name="StormChain",
        x=[f"K={int(k)}" for k in baseline["k"]],
        y=baseline["our_minutes_caught"] / 1000,
        marker_color=C["coral"],
        text=[f"+{v:.0f}%" for v in baseline["improvement_pct"]],
        textposition="outside", textfont=dict(color=C["gold"], size=14, family="Georgia"),
    ))
    fig_b.add_trace(go.Bar(
        name="Naive Baseline",
        x=[f"K={int(k)}" for k in baseline["k"]],
        y=baseline["naive_minutes_caught"] / 1000,
        marker_color=C["muted"],
    ))
    fig_b.update_layout(
        barmode="group", height=380,
        margin=dict(l=60, r=10, t=40, b=30),
        paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
        xaxis=dict(tickfont=dict(color=C["ice"], size=12), showgrid=False),
        yaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"],
                   title=dict(text="Cascade Minutes Caught (thousands)", font=dict(color=C["ice"]))),
        legend=dict(font=dict(color=C["ice"]), orientation="h", y=1.08),
    )
    st.plotly_chart(fig_b, use_container_width=True)

comment(
    "Cascade minutes caught at the same K value (number of pairs flagged)",
    "<strong>+78% at K=200</strong> — the sweet spot for real scheduling decisions",
    "<span class='insight'>→ 176 pairs StormChain flags that the naive approach misses entirely</span>",
    "These are pairs where A and B don't individually look bad — but their combined risk is high",
)


# =========================================================================
# § 04 — HOW THE MODEL SEES THE WORLD
# =========================================================================
section_header(
    "§ 04 / THE MODEL",
    "What drives cascading delays",
    "An XGBoost classifier trained on 1.9M synthetic pilot sequences, validated on held-out 2024 data.",
)

# Metrics row
mm_cols = st.columns(4)
mm_cols[0].metric("AUC-ROC", "0.81")
mm_cols[1].metric("AUC-PR", "0.12")
mm_cols[2].metric("Recall", "66%")
mm_cols[3].metric("Features", "117")

comment(
    "AUC-ROC 0.81 is strong — the model reliably discriminates cascading from non-cascading sequences",
    "<strong>AUC-PR looks low (0.12) — but that's expected</strong>: only 2.5% of sequences cascade, so precision-recall is naturally compressed",
    "<span class='insight'>→ This is why we use the model as a <strong>feature importance engine</strong>, not a per-flight classifier</span>",
    "The risk scoring model handles sparsity by aggregating to monthly pair-level statistics",
)

# ROC + PR side by side
curve_c1, curve_c2 = st.columns(2)
with curve_c1:
    if roc_curve is not None:
        fig_roc = go.Figure()
        fig_roc.add_trace(go.Scatter(
            x=roc_curve["fpr"], y=roc_curve["tpr"],
            mode="lines", fill="tozeroy",
            line=dict(color=C["coral"], width=2),
            fillcolor="rgba(255, 107, 107, 0.15)",
            name="StormChain",
        ))
        fig_roc.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode="lines", line=dict(color=C["muted"], width=1, dash="dash"), name="Random",
        ))
        fig_roc.update_layout(
            height=300,
            title=dict(text="ROC Curve · AUC 0.81", font=dict(color=C["white"], family="Georgia", size=13)),
            margin=dict(l=50, r=10, t=40, b=40),
            paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
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
            fillcolor="rgba(249, 178, 51, 0.15)",
            name="StormChain",
        ))
        fig_pr.update_layout(
            height=300,
            title=dict(text="Precision-Recall · AUC 0.12", font=dict(color=C["white"], family="Georgia", size=13)),
            margin=dict(l=50, r=10, t=40, b=40),
            paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
            xaxis=dict(title=dict(text="Recall", font=dict(color=C["ice"])),
                       tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
            yaxis=dict(title=dict(text="Precision", font=dict(color=C["ice"])),
                       tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
            showlegend=False,
        )
        st.plotly_chart(fig_pr, use_container_width=True)

if importance is not None:
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
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
        height=420,
        title=dict(text="Top 15 Features — What Drives Cascading Delays",
                   font=dict(color=C["white"], family="Georgia", size=14)),
        margin=dict(l=220, r=10, t=40, b=30),
        paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
        xaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
        yaxis=dict(tickfont=dict(color=C["ice"], family="Consolas", size=10)),
    )
    st.plotly_chart(fig_imp, use_container_width=True)

    comment(
        "<strong>Coral bars = DFW hub weather features</strong>, blue bars = other features",
        "DFW weather dominates because it affects <em>every</em> sequence",
        "<span class='insight'>→ This is a known limitation: in production, DFW weather should be a conditioning variable (\"given DFW forecast, which pairs need attention?\")</span>",
        "Pair-level features (B precipitation, connection minutes, endpoint dewpoints) still add meaningful signal",
    )


# =========================================================================
# § 05 — IMPACT & PAYOFF
# =========================================================================
section_header(
    "§ 05 / THE PAYOFF",
    "What this is worth in dollars",
    "Retrospective analysis on 5 years of historical data — how many cascading delay events would StormChain "
    "have flagged in advance, and what's that worth at the industry-standard $75/delay-minute rate.",
)

if sim_results is not None:
    imp_c1, imp_c2 = st.columns(2)
    with imp_c1:
        fig_sav = go.Figure()
        fig_sav.add_trace(go.Scatter(
            x=sim_results["k"], y=sim_results["dollar_savings"] / 1e6,
            mode="lines+markers", line=dict(color=C["coral"], width=3),
            marker=dict(size=12, color=C["gold"], line=dict(color=C["coral"], width=2)),
        ))
        fig_sav.update_layout(
            height=320,
            title=dict(text="Savings vs. Pairs Avoided (5-year total)",
                       font=dict(color=C["white"], family="Georgia", size=13)),
            margin=dict(l=50, r=10, t=40, b=40),
            paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
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
            marker_color=[C["teal"], C["teal"], C["gold"], C["coral"]],
            text=[f"{v:.1f}%" for v in sim_results["pct_events_prevented"]],
            textposition="outside", textfont=dict(color=C["white"], size=14),
        ))
        fig_pct.update_layout(
            height=320,
            title=dict(text="% of Cascading Events Prevented",
                       font=dict(color=C["white"], family="Georgia", size=13)),
            margin=dict(l=50, r=10, t=40, b=40),
            paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
            xaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
            yaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
        )
        st.plotly_chart(fig_pct, use_container_width=True)

    comment(
        "<strong>$438K/year adjusted</strong> (conservative) — <strong>$34.5M/year upper bound</strong> (if flagged pairs are systematically avoided)",
        "Real savings land between these bounds — targeted scheduling pushes toward the upper",
        "<span class='insight'>→ Extending to AA's other hubs (CLT, MIA, ORD, PHX, PHL) would multiply this 5-6×</span>",
    )

    # Full K-value table
    display = sim_results.copy()
    display["Dollar Savings (5yr)"] = display["dollar_savings"].apply(lambda x: f"${x/1e6:.1f}M")
    if "adjusted_savings" in display.columns:
        display["Adjusted (5yr)"] = display["adjusted_savings"].apply(lambda x: f"${x/1e3:.0f}K")
    display["% Prevented"] = display["pct_events_prevented"].apply(lambda x: f"{x:.2f}%")
    display["Events Prevented"] = display["prevented_events"].apply(lambda x: f"{int(x):,}")
    display["K"] = display["k"].astype(int)

    cols_to_show = ["K", "Events Prevented", "% Prevented", "Dollar Savings (5yr)"]
    if "Adjusted (5yr)" in display.columns:
        cols_to_show.append("Adjusted (5yr)")
    st.dataframe(display[cols_to_show], use_container_width=True, hide_index=True)

    # Monthly breakdown
    if monthly_breakdown is not None:
        best_k = int(sim_results["k"].max())
        mb = monthly_breakdown[monthly_breakdown["k"] == best_k].copy()
        month_names_full = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        mb["month_name"] = mb["month"].apply(lambda m: month_names_full[m-1])

        fig_mo = go.Figure()
        fig_mo.add_trace(go.Bar(
            x=mb["month_name"], y=mb["dollar_savings"] / 1e6,
            marker_color=[C["coral"] if v > mb["dollar_savings"].quantile(0.7)/1e6
                          else C["gold"] if v > mb["dollar_savings"].quantile(0.4)/1e6
                          else C["teal"]
                          for v in mb["dollar_savings"] / 1e6],
        ))
        fig_mo.update_layout(
            height=280,
            title=dict(text=f"Monthly Savings · K={best_k} (5-year totals)",
                       font=dict(color=C["white"], family="Georgia", size=13)),
            margin=dict(l=50, r=10, t=40, b=30),
            paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
            xaxis=dict(tickfont=dict(color=C["ice"]), showgrid=False),
            yaxis=dict(title=dict(text="Savings ($M)", font=dict(color=C["ice"])),
                       tickfont=dict(color=C["ice"]), gridcolor=C["border"]),
        )
        st.plotly_chart(fig_mo, use_container_width=True)

        comment(
            "<strong>May-July is where the money is</strong> — concentrated thunderstorm season",
            "<span class='insight'>→ February and October are quiet — the model's recommendations matter most in spring/summer</span>",
        )


# =========================================================================
# § 06 — CASE STUDY: MAY 28, 2024
# =========================================================================
section_header(
    "§ 06 / INCIDENT FORENSICS",
    "One day that cost $4.4M",
    "May 28, 2024 — the worst cascading delay day in the entire dataset. "
    "A single thunderstorm system moved through DFW at dawn and destroyed the day's schedule.",
)

if case_study is not None:
    # Incident log
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"""
        <div class="ops-panel">
            <p style='color: {C['gold']}; font-size: 11px; letter-spacing: 2px; margin-bottom: 12px;'>
                METAR 05:53 UTC
            </p>
            <p style='font-family: Consolas, monospace; color: {C['coral']}; font-size: 20px; margin-bottom: 12px; font-weight: bold;'>
                +TSRA FG SQ
            </p>
            <p style='color: {C['ice']}; font-size: 13px; margin-bottom: 16px;'>
                Heavy thunderstorm · fog · squall. Zero visibility reported at DFW.
            </p>
            <div style='display: flex; justify-content: space-between; padding-top: 12px; border-top: 1px solid {C['border']};'>
                <div>
                    <p style='color: {C['muted']}; font-size: 10px; letter-spacing: 2px; margin: 0;'>SEQUENCES</p>
                    <p style='color: {C['white']}; font-family: Georgia; font-size: 24px; font-weight: bold; margin: 0;'>170</p>
                </div>
                <div>
                    <p style='color: {C['muted']}; font-size: 10px; letter-spacing: 2px; margin: 0;'>PROPAGATED</p>
                    <p style='color: {C['coral']}; font-family: Georgia; font-size: 24px; font-weight: bold; margin: 0;'>149</p>
                </div>
                <div>
                    <p style='color: {C['muted']}; font-size: 10px; letter-spacing: 2px; margin: 0;'>COST</p>
                    <p style='color: {C['gold']}; font-family: Georgia; font-size: 24px; font-weight: bold; margin: 0;'>$4.4M</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        case_study["arr_hour"] = (case_study["inbound_arr_time"] // 60).astype(int)
        hourly = case_study.groupby("arr_hour")["total_cascade_minutes"].sum().reindex(range(6, 22), fill_value=0)

        fig_cs = go.Figure()
        colors_bar = [C["coral"] if v in hourly.nlargest(2).values else C["gold"]
                      for v in hourly.values]
        fig_cs.add_trace(go.Bar(
            x=[f"{h:02d}:00" for h in hourly.index],
            y=hourly.values, marker_color=colors_bar,
            hovertemplate="%{x}<br>%{y:,.0f} cascade min<extra></extra>",
        ))
        fig_cs.update_layout(
            height=260,
            margin=dict(l=50, r=10, t=10, b=30),
            paper_bgcolor=C["panel"], plot_bgcolor=C["panel"],
            xaxis=dict(tickfont=dict(color=C["ice"], size=10), showgrid=False),
            yaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"],
                       title=dict(text="Cascade Minutes", font=dict(color=C["ice"], size=11))),
        )
        st.plotly_chart(fig_cs, use_container_width=True)

    comment(
        "Hourly cascade delays on May 28, 2024 — by hour of inbound arrival at DFW",
        "<strong>Morning wave (07:00-09:00) concentrated 70% of damage</strong> as overnight delays propagated",
        "<span class='insight'>→ By noon the cascade had spread; by 14:00 airport operations stabilized but 200+ flights were already delayed</span>",
    )

    # Top cascading routes this day
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    case_pair_summary = case_study.groupby(["origin", "dest"]).agg(
        sequences=("total_cascade_minutes", "size"),
        total_cascade=("total_cascade_minutes", "sum"),
        avg_cascade=("total_cascade_minutes", "mean"),
        risk_score=("risk_score", "mean"),
    ).sort_values("total_cascade", ascending=False).head(15).reset_index()
    case_pair_summary["total_cascade"] = case_pair_summary["total_cascade"].round(0).astype(int)
    case_pair_summary["avg_cascade"] = case_pair_summary["avg_cascade"].round(0).astype(int)
    case_pair_summary["risk_score"] = case_pair_summary["risk_score"].round(1)
    case_pair_summary.columns = ["Origin", "Dest", "Sequences", "Total Cascade (min)", "Avg Cascade (min)", "Model Risk Score"]

    st.markdown(f"<p class='panel-title'>TOP 15 CASCADING PAIRS · MAY 28</p>", unsafe_allow_html=True)
    st.dataframe(case_pair_summary, use_container_width=True, hide_index=True)

    comment(
        "<strong>Many top-cascading pairs have low or zero model risk scores</strong> — our model missed them",
        "This is an <em>honest</em> finding, not a weakness: extreme weather events produce cascades on <strong>unusual route combinations</strong> (BOS-BHM, AMA-FLL) that monthly aggregation can't score",
        "<span class='insight'>→ StormChain's strength is <strong>predictable seasonal patterns</strong>, not one-off black swans — for extreme events, real-time monitoring complements the model</span>",
    )


# =========================================================================
# § 07 — PAIR EXPLORER
# =========================================================================
section_header(
    "§ 07 / INVESTIGATE",
    "Query any airport pair",
    "Pick any two airports below to see their full monthly risk breakdown — when they're dangerous together, and when they're fine.",
)

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
        x=MONTH_NAMES, y=pair_data["risk_score"],
        marker_color=[C["coral"] if r >= 80 else C["gold"] if r >= 65 else C["teal"]
                      for r in pair_data["risk_score"]],
        text=[f"{r:.0f}" for r in pair_data["risk_score"]],
        textposition="outside", textfont=dict(color=C["white"], size=11),
    ))
    fig_pair.update_layout(
        height=300,
        title=dict(text=f"Monthly Risk · {airport_a} ↔ {airport_b}",
                   font=dict(color=C["white"], family="Georgia", size=14)),
        margin=dict(l=40, r=10, t=40, b=20),
        paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
        xaxis=dict(tickfont=dict(color=C["ice"]), showgrid=False),
        yaxis=dict(tickfont=dict(color=C["ice"]), gridcolor=C["border"],
                   range=[0, 110]),
    )
    st.plotly_chart(fig_pair, use_container_width=True)

    peak_mo = MONTH_NAMES[pair_data.loc[pair_data["risk_score"].idxmax(), "month"]-1]
    avg_risk = pair_data["risk_score"].mean()
    peak_risk = pair_data["risk_score"].max()
    joint_wx = pair_data["joint_weather_delay_prob"].mean()

    comment(
        f"<strong>{airport_a} ↔ {airport_b}</strong>: peaks at <strong>{peak_risk:.0f}</strong> in {peak_mo}, averages {avg_risk:.0f} year-round",
        f"Joint weather delay probability (both airports impacted same day): {joint_wx:.3f}",
        "<span class='insight'>→ Color code: coral ≥80 (critical), gold 65-80 (high), teal <65 (moderate)</span>",
    )


# =========================================================================
# § 08 — THE PRODUCT
# =========================================================================
section_header(
    "§ 08 / THE PRODUCT",
    "1,220 avoid recommendations · 294 swap alternatives",
    "Not a risk score. A concrete list of pair-season combinations to avoid in pilot sequencing, "
    "with safe alternative destinations for each flagged pair.",
)

if avoid_list is not None:
    season_filter = st.selectbox(
        "Filter by season",
        ["All"] + sorted(avoid_list["season"].unique()),
        key="avoid_season",
    )
    display_av = avoid_list if season_filter == "All" else avoid_list[avoid_list["season"] == season_filter]
    st.markdown(f"<p class='panel-title'>AVOID LIST · {len(display_av)} RECOMMENDATIONS</p>", unsafe_allow_html=True)
    st.dataframe(
        display_av[["season", "airport_a", "airport_b", "risk_score", "reason"]].head(100),
        use_container_width=True, height=360, hide_index=True,
    )

comment(
    "<strong>Each row is a specific recommendation</strong> with the primary reason (correlated weather, tight turnaround, duty time risk, etc.)",
    "<span class='insight'>→ This is the product: what to avoid, when, and why</span>",
)

if swap_recs is not None:
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    st.markdown(f"<p class='panel-title'>SWAP RECOMMENDATIONS · {len(swap_recs)} ALTERNATIVES</p>", unsafe_allow_html=True)
    st.dataframe(
        swap_recs[["season", "avoid_origin", "avoid_dest", "avoid_risk",
                   "swap_dest", "swap_risk", "risk_reduction"]].head(50),
        use_container_width=True, height=360, hide_index=True,
    )
    avg_red = swap_recs['risk_reduction'].mean()
    comment(
        f"<strong>Average risk reduction per swap: {avg_red:.0f} points</strong>",
        "Example: MCO→DFW→MIA (risk 96) → swap to MCO→DFW→HRL (risk 30) saves 66 risk points",
        "<span class='insight'>→ Every flagged pair has at least one safe swap alternative that AA already flies</span>",
    )


# =========================================================================
# § FINAL — CLOSING STATEMENT
# =========================================================================
_closing_html = (
    '<div class="closing">'
    '<span class="closing-kicker">§ FINAL / SYSTEM READY</span>'
    '<h2 class="closing-title">Weather will happen.<br>Cascading delays don\'t have to.</h2>'
    '<p class="closing-tagline">'
    'On May 28, 2024 a storm cost $4.4M in a single day. '
    'We can\'t stop the storms — but we can stop scheduling pilots into the path of every '
    'one of them. StormChain identifies the 1,220 specific pair-month combinations worth '
    'avoiding and offers a safer alternative for each.'
    '</p>'
    '<div class="closing-ascii">'
    '<span class="line-ok">[ OK ]</span> Data pipeline — 842K flights, 3.5M weather obs, 3.3M METAR<br>'
    '<span class="line-ok">[ OK ]</span> Model trained — XGBoost AUC-ROC 0.81, +78% vs. naive baseline<br>'
    '<span class="line-ok">[ OK ]</span> Risk scoring — 37,920 pair-month scores, monthly granularity<br>'
    '<span class="line-ok">[ OK ]</span> Avoid list — 1,220 recommendations across 4 seasons<br>'
    '<span class="line-ok">[ OK ]</span> Swap alternatives — 294 safer pairings, AA already flies all of them<br>'
    '<span class="line-info">[ LIVE ]</span> Dashboard — deployed, inspectable, ready for integration<br><br>'
    '<span class="line-info">// next step: plug into crew scheduling system</span><br>'
    '<span class="line-info">// next step: extend to CLT, MIA, ORD, PHX, PHL hubs</span><br>'
    '<span class="line-info">// next step: live TAF forecasts for forward-looking scheduling</span>'
    '</div>'
    '<div class="closing-cta">'
    'STORMCHAIN · EPPS-AMERICAN AIRLINES DATA CHALLENGE · GROW 26.2<br>'
    '<a href="https://github.com/drPod/stormchain" target="_blank">github.com/drPod/stormchain</a> · '
    '<a href="https://stormchain.streamlit.app" target="_blank">stormchain.streamlit.app</a>'
    '</div>'
    '</div>'
)
st.markdown(_closing_html, unsafe_allow_html=True)
