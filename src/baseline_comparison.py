"""Compare our model vs. naive baseline to prove value-add."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    PROCESSED_DIR, MODEL_DIR, SIMULATION_DIR, OUTPUT_DIR,
    DFW_IATA, DELAY_THRESHOLD_MINUTES, COST_PER_DELAY_MINUTE,
)


def run_baseline_comparison() -> pd.DataFrame:
    """Compare our model vs naive "avoid two individually bad airports" baseline.

    Naive baseline: flag pairs where BOTH airports individually have
    weather_delay_rate above median. This is the simplest possible approach.

    Our model: flag pairs by composite risk score.

    Metric: for the same number of flagged pairs (K), which approach
    catches more actual cascading delay events? (Precision at K)
    """
    risk_scores = pd.read_parquet(MODEL_DIR / "risk_scores.parquet")
    flights = pd.read_parquet(PROCESSED_DIR / "flights_dfw.parquet")
    flights["FlightDate"] = pd.to_datetime(flights["FlightDate"])
    flights["date"] = flights["FlightDate"].dt.normalize()

    # Build actual cascading events (same as simulation.py)
    inbound = flights[(flights["Dest"] == DFW_IATA) & (flights["WeatherDelay"] > 0)].copy()
    inbound["airport"] = inbound["Origin"]
    outbound = flights[(flights["Origin"] == DFW_IATA) & (flights["DepDelay"] > DELAY_THRESHOLD_MINUTES)].copy()
    outbound["airport"] = outbound["Dest"]

    inbound_daily = inbound.groupby(["airport", "date"]).agg(
        in_delay=("WeatherDelay", "sum"),
    ).reset_index()
    outbound_daily = outbound.groupby(["airport", "date"]).agg(
        out_delay=("DepDelay", "sum"),
    ).reset_index()

    cascading = inbound_daily.merge(outbound_daily, on="date", suffixes=("_in", "_out"))
    cascading = cascading[cascading["airport_in"] != cascading["airport_out"]]
    cascading["pair_a"] = cascading[["airport_in", "airport_out"]].min(axis=1)
    cascading["pair_b"] = cascading[["airport_in", "airport_out"]].max(axis=1)
    cascading["month"] = cascading["date"].dt.month
    cascading["cascade_minutes"] = cascading["out_delay"]

    # Aggregate actual cascading events per pair-month
    actual = cascading.groupby(["pair_a", "pair_b", "month"]).agg(
        actual_events=("cascade_minutes", "size"),
        actual_minutes=("cascade_minutes", "sum"),
    ).reset_index()

    print(f"Actual cascading events: {len(actual):,} pair-month combinations")
    print(f"Total cascade minutes: {actual['actual_minutes'].sum():,.0f}")

    # --- NAIVE BASELINE ---
    # Per-airport weather delay rate
    all_flights = flights.copy()
    all_flights["other"] = np.where(all_flights["Origin"] == DFW_IATA, all_flights["Dest"], all_flights["Origin"])
    airport_risk = all_flights.groupby(["other", "Month"]).agg(
        weather_delay_rate=("WeatherDelay", lambda x: (x > 0).mean()),
    ).reset_index()

    # Median weather delay rate per month
    median_rate = airport_risk.groupby("Month")["weather_delay_rate"].median().to_dict()

    # Naive: both airports above median for that month
    naive_pairs = risk_scores.copy()
    naive_pairs["a_rate"] = naive_pairs.apply(
        lambda r: airport_risk[
            (airport_risk["other"] == r["airport_a"]) & (airport_risk["Month"] == r["month"])
        ]["weather_delay_rate"].values[0] if len(airport_risk[
            (airport_risk["other"] == r["airport_a"]) & (airport_risk["Month"] == r["month"])
        ]) > 0 else 0,
        axis=1,
    )
    naive_pairs["b_rate"] = naive_pairs.apply(
        lambda r: airport_risk[
            (airport_risk["other"] == r["airport_b"]) & (airport_risk["Month"] == r["month"])
        ]["weather_delay_rate"].values[0] if len(airport_risk[
            (airport_risk["other"] == r["airport_b"]) & (airport_risk["Month"] == r["month"])
        ]) > 0 else 0,
        axis=1,
    )
    naive_pairs["naive_score"] = naive_pairs["a_rate"] * naive_pairs["b_rate"]

    # --- COMPARISON ---
    k_values = [50, 100, 200, 500]
    results = []

    for k in k_values:
        # Our model: top K by risk_score
        our_top = risk_scores.nlargest(k, "risk_score")
        our_pairs = set(zip(our_top["airport_a"], our_top["airport_b"], our_top["month"]))

        # Naive: top K by naive_score
        naive_top = naive_pairs.nlargest(k, "naive_score")
        naive_set = set(zip(naive_top["airport_a"], naive_top["airport_b"], naive_top["month"]))

        # How many actual cascade events does each catch?
        our_caught = actual[actual.apply(
            lambda r: (r["pair_a"], r["pair_b"], r["month"]) in our_pairs, axis=1
        )]
        naive_caught = actual[actual.apply(
            lambda r: (r["pair_a"], r["pair_b"], r["month"]) in naive_set, axis=1
        )]

        our_minutes = our_caught["actual_minutes"].sum()
        naive_minutes = naive_caught["actual_minutes"].sum()
        total_minutes = actual["actual_minutes"].sum()

        improvement = (our_minutes - naive_minutes) / max(naive_minutes, 1) * 100

        results.append({
            "k": k,
            "our_events_caught": len(our_caught),
            "naive_events_caught": len(naive_caught),
            "our_minutes_caught": our_minutes,
            "naive_minutes_caught": naive_minutes,
            "total_minutes": total_minutes,
            "our_pct": our_minutes / max(total_minutes, 1) * 100,
            "naive_pct": naive_minutes / max(total_minutes, 1) * 100,
            "improvement_pct": improvement,
        })

        print(f"\nK={k}:")
        print(f"  Our model:     {our_minutes:>12,.0f} cascade minutes caught ({our_minutes/max(total_minutes,1)*100:.2f}%)")
        print(f"  Naive baseline:{naive_minutes:>12,.0f} cascade minutes caught ({naive_minutes/max(total_minutes,1)*100:.2f}%)")
        print(f"  Improvement:   {improvement:>+.1f}%")

    results_df = pd.DataFrame(results)
    results_df.to_parquet(OUTPUT_DIR / "baseline_comparison.parquet", index=False)

    # Overlap analysis: how many pairs are in both?
    our_500 = set(zip(risk_scores.nlargest(500, "risk_score")["airport_a"],
                      risk_scores.nlargest(500, "risk_score")["airport_b"]))
    naive_500 = set(zip(naive_pairs.nlargest(500, "naive_score")["airport_a"],
                        naive_pairs.nlargest(500, "naive_score")["airport_b"]))
    overlap = our_500 & naive_500
    only_ours = our_500 - naive_500
    only_naive = naive_500 - our_500

    print(f"\nPair overlap (K=500):")
    print(f"  In both: {len(overlap)}")
    print(f"  Only our model: {len(only_ours)} (pairs our model catches that naive misses)")
    print(f"  Only naive: {len(only_naive)} (pairs naive catches that our model misses)")

    return results_df


if __name__ == "__main__":
    results = run_baseline_comparison()
    print(f"\nResults:\n{results.to_string(index=False)}")
