"""Run modeling + simulation steps after feature engineering is done.
Assumes processed parquet files exist in data/processed/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import PROCESSED_DIR, MODEL_DIR

def main():
    import pandas as pd

    # Check prerequisites
    pairs_path = PROCESSED_DIR / "airport_pairs.parquet"
    sequences_path = PROCESSED_DIR / "sequences.parquet"

    if not pairs_path.exists():
        print("airport_pairs.parquet not found - run feature engineering first")
        return
    if not sequences_path.exists():
        print("sequences.parquet not found - run feature engineering first")
        return

    pairs = pd.read_parquet(pairs_path)
    sequences = pd.read_parquet(sequences_path)
    print(f"Pairs: {pairs.shape}, Sequences: {sequences.shape}")

    # Step 1: Risk scores
    print("\n[1/4] Computing risk scores ...")
    from src.modeling import compute_risk_scores
    risk_scores = compute_risk_scores(pairs)
    print(f"Top 10 riskiest pairs:")
    print(risk_scores.nlargest(10, "risk_score")[
        ["airport_a", "airport_b", "month", "risk_score"]
    ].to_string(index=False))

    # Step 2: Enrich sequences with pair features
    print("\n[2/4] Enriching sequences ...")
    from src.data_processing import load_weather, compute_daily_weather
    from src.feature_engineering import enrich_sequences_with_features

    weather = load_weather()
    daily_weather = compute_daily_weather(weather)
    enriched = enrich_sequences_with_features(sequences, pairs, daily_weather)
    print(f"Enriched sequences: {enriched.shape}")

    # Step 3: Train XGBoost
    print("\n[3/4] Training XGBoost ...")
    from src.modeling import train_xgboost, update_risk_weights_from_importance
    result = train_xgboost(enriched)

    print("\nUpdating risk weights ...")
    updated_scores = update_risk_weights_from_importance(pairs, result["importance"])

    # Step 4: Simulation
    print("\n[4/4] Running Monte Carlo simulation ...")
    from src.data_processing import load_flights
    from src.simulation import run_simulation

    flights = load_flights()
    sim_results = run_simulation(flights, updated_scores)
    print(f"Simulation: {sim_results.shape}")

    print("\n" + "=" * 60)
    print("ALL STEPS COMPLETE")
    print("=" * 60)
    print("Launch dashboard: .venv/bin/streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
