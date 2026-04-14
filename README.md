# StormChain

**Airline Crew Sequences Meet Bad Weather — EPPS-American Airlines Data Challenge (GROW 26.2)**

A data-driven system that identifies pilot flight sequences through DFW most vulnerable to weather-driven cascading delays, produces an actionable avoid list with swap recommendations, and validates the approach with a cascade-propagation model.

*Named for the phenomenon it models: chains of cascading delays triggered by correlated weather events propagating through pilot sequences.*

## Quick Results

- **AUC-ROC 0.81** on held-out 2024 data (XGBoost, 117 features, 1.5M training samples)
- **+78% more cascading delay minutes caught than a naive baseline** at K=200
- **1,220 concrete avoid recommendations** across 4 seasons with **294 swap alternatives**
- **$34.5M upper-bound / $438K adjusted** annual savings at K=500 pairs avoided
- **All 4 challenge objectives addressed**: delay propagation, duty time violations, missed connections, fatigue

## Dataset Scale

| Dataset | Volume | Source |
|---|---|---|
| Flight records | 842,000 flights (2019-2024) | BTS via Kaggle |
| General weather | 3,505,920 hourly obs, 80 airports | Open-Meteo API |
| Aviation weather (METAR) | 3,265,456 obs, 75 airports | Iowa Environmental Mesonet |
| Synthetic pilot sequences | 1,899,119 | Derived from BTS |

## Repository Layout

```
stormchain/
├── report/                 # 20-page competition submission
│   ├── report.pdf
│   ├── report.md
│   ├── presentation.pptx   # 7-minute slide deck
│   └── presentation.html   # Reveal.js version
├── docs/
│   └── methodology_evolution.md  # How the methodology was iteratively improved
├── src/                    # Core pipeline
│   ├── data_acquisition.py
│   ├── data_processing.py
│   ├── feature_engineering.py
│   ├── metar_processing.py
│   ├── modeling.py
│   ├── simulation.py
│   ├── recommendations.py
│   ├── baseline_comparison.py
│   └── case_study.py
├── app/                    # Interactive Streamlit dashboard
│   └── streamlit_app.py
├── outputs/                # Selected results (avoid lists, summaries)
├── config.py
├── run_pipeline.py         # End-to-end orchestrator
└── requirements.txt
```

## Getting Started

```bash
# 1. Set up environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure data access
echo "KAGGLE_API_TOKEN=your_token_here" > .env

# 3. Run the full pipeline (takes ~20 minutes)
python run_pipeline.py

# 4. Launch the interactive dashboard
streamlit run app/streamlit_app.py
```

## Key Insight

The most instructive finding: **the worst cascading pairs aren't necessarily weather-correlated.** On May 28, 2024 (our worst day), IAH-LAX cascaded not because Houston and LA share weather, but because Houston's weather delay ate into the DFW turnaround for a high-volume LA route. Our model captures both correlated-weather risk and operational turnaround risk, which explains why it outperforms the naive "avoid two bad airports" baseline by 78%.

## Methodology Evolution

This project went through 12 iterations of self-critique and improvement. See `docs/methodology_evolution.md` for the full record — what we built, what we broke, and what we learned. Each identified gap made the analysis stronger. Highlights:

- Realized the PDF says "flights" not "airports" — added temporal dimension
- Discovered our impact estimates were inflated 240× — rebuilt with realistic pilot-sequence counting
- Found DFW weather dominated XGBoost features — added pair-level risk scoring to mitigate
- Integrated real METAR aviation weather data after realizing proxies weren't good enough

## Links

- **Repository:** https://github.com/drPod/stormchain
- **Interactive Dashboard:** deployed on Streamlit Community Cloud (URL added after deployment)
- **Report:** `report/report.pdf`
- **Presentation:** `report/presentation.pptx`

## License

Academic submission for EPPS-AA Data Challenge GROW 26.2. Code provided for review purposes.
