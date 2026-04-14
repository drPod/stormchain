"""End-to-end pipeline orchestrator. Run with: python run_pipeline.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import PROCESSED_DIR, MODEL_DIR, SIMULATION_DIR


def main():
    print("=" * 60)
    print("AA CREW SEQUENCE WEATHER RISK PIPELINE")
    print("=" * 60)

    # Step 1: Ensure airport reference data exists
    print("\n[1/7] Airport reference data ...")
    from src.airport_reference import build_airports_csv, load_airports
    airports = load_airports()
    print(f"  {len(airports)} airports loaded")

    # Step 2: Download and filter BTS data
    print("\n[2/7] BTS flight delay data ...")
    from src.data_acquisition import load_and_filter_bts
    flights = load_and_filter_bts()
    print(f"  {len(flights):,} DFW flights loaded")

    # Step 3: Download weather data
    print("\n[3/7] Weather data ...")
    from src.data_acquisition import fetch_all_weather
    weather = fetch_all_weather(airports)
    print(f"  {len(weather):,} weather records loaded")

    # Step 4: Process and merge
    print("\n[4/7] Data processing ...")
    from src.data_processing import compute_daily_weather, merge_flights_with_daily_weather
    daily_weather = compute_daily_weather(weather)
    print(f"  Daily weather: {len(daily_weather):,} rows")
    merged = merge_flights_with_daily_weather(flights, daily_weather)
    print(f"  Merged flights+weather: {len(merged):,} rows")

    # Step 5: Feature engineering
    print("\n[5/7] Feature engineering ...")
    from src.feature_engineering import (
        compute_airport_monthly_stats,
        compute_airport_monthly_weather,
        compute_pair_features,
        enrich_sequences_with_features,
    )
    from src.data_processing import build_synthetic_sequences

    airport_stats = compute_airport_monthly_stats(flights)
    print(f"  Airport stats: {len(airport_stats):,} rows")

    airport_weather = compute_airport_monthly_weather(daily_weather)
    print(f"  Airport weather: {len(airport_weather):,} rows")

    pairs = compute_pair_features(flights, daily_weather, airports)
    print(f"  Pair features: {len(pairs):,} rows")

    sequences = build_synthetic_sequences(flights)
    print(f"  Synthetic sequences: {len(sequences):,} rows")

    enriched = enrich_sequences_with_features(sequences, pairs, daily_weather)
    print(f"  Enriched sequences: {len(enriched):,} rows")

    # Step 6: Modeling
    print("\n[6/7] Modeling ...")
    from src.modeling import compute_risk_scores, train_xgboost, update_risk_weights_from_importance

    risk_scores = compute_risk_scores(pairs)
    print(f"  Risk scores: {len(risk_scores):,} rows")

    print("\n  Training XGBoost ...")
    result = train_xgboost(enriched)
    print(f"  AUC-ROC: {result['metrics']['auc_roc']:.4f}")
    print(f"  AUC-PR: {result['metrics']['auc_pr']:.4f}")

    updated_scores = update_risk_weights_from_importance(pairs, result["importance"])

    print("\n  Top 10 riskiest pairs:")
    top10 = updated_scores.nlargest(10, "risk_score")[
        ["airport_a", "airport_b", "month", "risk_score"]
    ]
    print(top10.to_string(index=False))

    # Step 7: Simulation
    print("\n[7/7] Monte Carlo simulation ...")
    from src.simulation import run_simulation
    sim_results = run_simulation(flights, updated_scores)
    print(f"  Simulation complete: {len(sim_results)} trials")

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"\nTo launch dashboard: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
