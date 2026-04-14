<div align="center">

# ⛈️ StormChain

### Airline Crew Sequences Meet Bad Weather

Identifying pilot flight sequences through DFW most vulnerable to weather-driven cascading delays — with a live interactive dashboard, a validated XGBoost model, and 1,220 concrete avoid recommendations.

**[🚀 Live Dashboard](https://stormchain.streamlit.app)** · **[📄 Report PDF](report/report.pdf)** · **[🎤 Presentation](report/presentation.pptx)**

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://stormchain.streamlit.app)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## What it does

When weather hits one airport, it cascades. A pilot's inbound from MCO arrives late at DFW, their outbound to MIA departs late, passengers miss connections, and the delay ripples through the entire network. **On May 28, 2024, one thunderstorm system at DFW triggered cascading delays costing $4.4M in a single day.**

StormChain identifies which pilot flight pairings through DFW are most vulnerable to this — by month, by airport pair — and recommends safer alternatives.

## Headline numbers

| Metric | Value |
|---|---|
| Model AUC-ROC (2024 holdout) | **0.81** |
| Improvement over naive baseline at K=200 | **+78%** |
| Concrete avoid recommendations | **1,220** |
| Safe swap alternatives | **294** |
| Total data ingested | **842K flights · 3.5M weather obs · 3.3M METAR obs** |
| Features in model | **117** |

## Data sources

- **BTS On-Time Performance** — 842K DFW flight records (2019–2024, excluding COVID-anomalous 2020)
- **Open-Meteo Historical API** — 3.5M hourly weather observations across 80 US airports
- **Iowa Environmental Mesonet (IEM) ASOS** — 3.3M real METAR observations with actual ceiling height, visibility, and weather codes
- **AWC Aviation Weather Center API** — live current METAR for real-time dashboard conditions

## Architecture

```
├── report/
│   ├── report.pdf              ← the 20-page competition submission
│   ├── presentation.pptx       ← 10-slide deck for finalist presentation
│   ├── build_deck.js           ← pptxgenjs source for the deck
│   └── presentation.html       ← reveal.js fallback
├── app/
│   └── streamlit_app.py        ← tactical OCC dashboard (single-page scrollytelling)
├── src/
│   ├── data_acquisition.py     ← BTS (Kaggle) + Open-Meteo downloaders
│   ├── metar_processing.py     ← METAR → daily IFR/ceiling/visibility features
│   ├── data_processing.py      ← clean, merge, daily aggregation
│   ├── feature_engineering.py  ← airport-pair features (weather correlation,
│   │                             missed connection risk, duty time, fatigue)
│   ├── modeling.py             ← XGBoost + composite risk scoring
│   ├── simulation.py           ← cascade propagation + retrospective impact analysis
│   ├── case_study.py           ← May 28, 2024 deep dive
│   ├── baseline_comparison.py  ← proof vs. naive approach
│   ├── recommendations.py      ← avoid list + swap recommendations + seasonal
│   ├── generate_report_figures.py  ← matplotlib figures for the PDF
│   └── airport_reference.py    ← IATA → coordinates/timezone/region
├── docs/
│   └── methodology_evolution.md  ← honest record of 12 problems found + fixed
├── outputs/
│   ├── avoid_list.csv          ← 1,220 pair-season recommendations
│   ├── swap_recommendations.csv  ← 294 safer alternatives
│   ├── seasonal_summary.csv    ← top pairs per season
│   ├── model/                  ← XGBoost artifacts, ROC/PR curves
│   ├── simulation/             ← impact analysis results
│   └── figures/                ← PNG figures embedded in the report
├── fetch_metar.py              ← IEM ASOS downloader (METAR data)
├── run_pipeline.py             ← end-to-end orchestrator
├── config.py                   ← constants, paths, API params
└── requirements.txt
```

## Running locally

```bash
# 1. Set up environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. (Optional) Configure Kaggle for BTS data downloads
echo "KAGGLE_API_TOKEN=your_token_here" > .env

# 3. Run the full pipeline (~25 min; caches to parquet)
python run_pipeline.py

# 4. Launch the dashboard
streamlit run app/streamlit_app.py
```

## Methodology highlights

This project went through **12 documented iterations** of self-critique. Every gap found made the analysis stronger:

1. Added FAA Part 117 duty time features
2. Added WOCL fatigue exposure scoring
3. Modeled missed connections explicitly (not just delays)
4. Built cascade propagation physics (not just binary co-occurrence)
5. Integrated real METAR aviation weather (not just general meteorology)
6. Caught and corrected a 240× inflated case study cost estimate
7. Added assignment-probability scaling to impact numbers
8. Reframed XGBoost's low AUC-PR as expected for rare events
9. Identified time-of-day patterns within hourly weather data
10. Built an actual avoid list + swap recommendations (not just risk scores)
11. Ran a concrete case study on the worst day in the data
12. Compared against a naive baseline to prove value-add

Full record in [`docs/methodology_evolution.md`](docs/methodology_evolution.md).

## Key insight

The most instructive finding came from the May 28, 2024 case study: **the worst cascading pairs aren't always weather-correlated.** On that day, IAH→DFW→LAX was the worst actual pair — not because Houston and LA share weather (they don't), but because Houston's weather delay ate into the DFW turnaround for a high-volume LA route.

This reframes the problem: it isn't just about correlated weather at endpoints. It's about which airports generate delays that propagate through DFW's tight scheduling windows.

## Credits

Built for the **EPPS-American Airlines Data Challenge (GROW 26.2)** by [drPod](https://github.com/drPod), a student at UIUC.

## License

[MIT](LICENSE) — free to use, modify, and learn from.
