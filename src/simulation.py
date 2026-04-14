"""Retrospective analysis: quantify delay savings from avoiding risky pairs."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    PROCESSED_DIR, SIMULATION_DIR, MODEL_DIR,
    TOP_K_VALUES, COST_PER_DELAY_MINUTE,
    DFW_IATA, DELAY_THRESHOLD_MINUTES,
)


def compute_cascade_propagation(
    flights_df: pd.DataFrame,
    risk_scores_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute actual propagated delay minutes for each airport pair.

    For each synthetic sequence A→DFW→B:
      propagated_delay = max(0, inbound_arr_delay - turnaround_gap)
      total_cascade = propagated_delay + outbound_weather_delay

    This gives us actual delay minutes attributable to the pairing decision.
    """
    flights = flights_df.copy()
    flights["date"] = flights["FlightDate"].dt.normalize()

    inbound = flights[flights["Dest"] == DFW_IATA].copy()
    outbound = flights[flights["Origin"] == DFW_IATA].copy()

    # Need arrival time and departure time
    inbound = inbound.dropna(subset=["CRSArrTime", "ArrDelay"])
    outbound = outbound.dropna(subset=["CRSDepTime", "DepDelay"])

    def hhmm_to_min(t):
        t = int(t)
        return (t // 100) * 60 + (t % 100)

    inbound["arr_min"] = inbound["CRSArrTime"].apply(hhmm_to_min)
    outbound["dep_min"] = outbound["CRSDepTime"].apply(hhmm_to_min)

    # Only weather-delayed inbound flights
    wx_inbound = inbound[inbound["WeatherDelay"] > 0].copy()

    # For each date, compute propagation
    dates = sorted(flights["date"].unique())
    pair_cascades = {}  # (pair_a, pair_b, month) -> list of cascade minutes

    print(f"Computing cascade propagation across {len(dates)} days ...")
    for i, date in enumerate(dates):
        if (i + 1) % 200 == 0:
            print(f"  Day {i+1}/{len(dates)} ...")

        day_wx_in = wx_inbound[wx_inbound["date"] == date]
        day_out = outbound[(outbound["date"] == date) & (outbound["DepDelay"] > 0)]

        if len(day_wx_in) == 0 or len(day_out) == 0:
            continue

        # Sample to keep tractable
        if len(day_wx_in) > 30:
            day_wx_in = day_wx_in.sample(30, random_state=42)
        if len(day_out) > 30:
            day_out = day_out.sample(30, random_state=42)

        month = date.month

        for _, inf in day_wx_in.iterrows():
            for _, outf in day_out.iterrows():
                gap = outf["dep_min"] - inf["arr_min"]
                if gap < 45 or gap > 480:
                    continue

                origin = inf["Origin"]
                dest = outf["Dest"]
                if origin == dest:
                    continue

                arr_delay = inf["ArrDelay"]
                propagated = max(0, arr_delay - gap)
                outbound_wx = outf.get("WeatherDelay", 0) or 0
                total_cascade = propagated + outbound_wx

                if total_cascade <= 0:
                    continue

                pair_a = min(origin, dest)
                pair_b = max(origin, dest)
                key = (pair_a, pair_b, month)

                if key not in pair_cascades:
                    pair_cascades[key] = []
                pair_cascades[key].append(total_cascade)

    # Aggregate
    rows = []
    for (pair_a, pair_b, month), delays in pair_cascades.items():
        rows.append({
            "airport_a": pair_a,
            "airport_b": pair_b,
            "month": month,
            "cascade_events": len(delays),
            "total_cascade_minutes": sum(delays),
            "avg_cascade_minutes": sum(delays) / len(delays),
            "cascade_cost": sum(delays) * COST_PER_DELAY_MINUTE,
        })

    cascade_df = pd.DataFrame(rows).sort_values("total_cascade_minutes", ascending=False)
    cascade_df.to_parquet(SIMULATION_DIR / "cascade_propagation.parquet", index=False)

    print(f"\nPairs with cascade propagation: {len(cascade_df):,}")
    print(f"Total propagated delay: {cascade_df['total_cascade_minutes'].sum():,.0f} minutes")
    print(f"Total cascade cost: ${cascade_df['cascade_cost'].sum():,.0f}")

    print(f"\nTop 15 pairs by propagated delay:")
    top = cascade_df.head(15)
    print(top[["airport_a", "airport_b", "month", "cascade_events",
               "avg_cascade_minutes", "cascade_cost"]].to_string(index=False))

    return cascade_df


def run_simulation(
    flights_df: pd.DataFrame,
    risk_scores_df: pd.DataFrame,
    top_k_values: list[int] = TOP_K_VALUES,
    **kwargs,
) -> pd.DataFrame:
    """Retrospective analysis: how many actual cascading delays would our model
    have prevented by flagging risky pairs?

    For every actual day in the data, we find all pairs (A, B) where:
    - An inbound flight from A arrived at DFW with a weather delay
    - An outbound flight to B departed DFW with a delay (any cause)
    - Both occurred on the same day

    These are "cascading delay events." We then check: was (A, B) in our
    top-K risky pairs? If yes, we could have prevented it by not scheduling
    that sequence. The prevented delay minutes × $75 = savings.
    """
    SIMULATION_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = SIMULATION_DIR / "monte_carlo_results.parquet"

    flights = flights_df.copy()
    flights["date"] = flights["FlightDate"].dt.normalize()

    # Inbound flights with weather delay
    inbound = flights[
        (flights["Dest"] == DFW_IATA) &
        (flights["WeatherDelay"] > 0)
    ].copy()
    inbound["airport"] = inbound["Origin"]

    # Outbound flights with any significant delay
    outbound = flights[
        (flights["Origin"] == DFW_IATA) &
        (flights["DepDelay"] > DELAY_THRESHOLD_MINUTES)
    ].copy()
    outbound["airport"] = outbound["Dest"]

    print(f"Inbound weather-delayed flights: {len(inbound):,}")
    print(f"Outbound delayed flights (>{DELAY_THRESHOLD_MINUTES}min): {len(outbound):,}")

    # Find cascading delay events: same day, inbound weather delay + outbound delay
    inbound_daily = inbound.groupby(["airport", "date"]).agg(
        inbound_weather_delay=("WeatherDelay", "sum"),
        inbound_flights=("WeatherDelay", "size"),
        inbound_avg_delay=("ArrDelay", "mean"),
    ).reset_index()

    outbound_daily = outbound.groupby(["airport", "date"]).agg(
        outbound_delay=("DepDelay", "sum"),
        outbound_flights=("DepDelay", "size"),
        outbound_avg_delay=("DepDelay", "mean"),
    ).reset_index()

    # Cross-join: for each day, every impacted inbound airport × every impacted outbound airport
    cascading = inbound_daily.merge(outbound_daily, on="date", suffixes=("_in", "_out"))
    # Remove same-airport pairs
    cascading = cascading[cascading["airport_in"] != cascading["airport_out"]]
    cascading["month"] = cascading["date"].dt.month

    # The cascade delay = the delay minutes that could be avoided
    # If inbound from A is weather-delayed and outbound to B is delayed,
    # the outbound delay is partly caused by the cascade
    cascading["cascade_minutes"] = cascading["outbound_avg_delay"]

    print(f"Cascading delay events (airport-pair-days): {len(cascading):,}")
    print(f"Total cascade delay minutes: {cascading['cascade_minutes'].sum():,.0f}")

    # Normalize pair keys to match risk_scores (alphabetical order)
    cascading["pair_a"] = cascading[["airport_in", "airport_out"]].min(axis=1)
    cascading["pair_b"] = cascading[["airport_in", "airport_out"]].max(axis=1)

    # For each K, check how many cascading events our model would have caught
    results_rows = []
    for k in top_k_values:
        top_k = risk_scores_df.nlargest(k, "risk_score")

        # Build set of risky pairs (both directions)
        risky_pairs = set()
        for _, row in top_k.iterrows():
            risky_pairs.add((row["airport_a"], row["airport_b"]))

        # Check which cascading events match a risky pair
        cascading[f"flagged_k{k}"] = cascading.apply(
            lambda r: (r["pair_a"], r["pair_b"]) in risky_pairs, axis=1
        )

        flagged = cascading[cascading[f"flagged_k{k}"]]
        prevented_minutes = flagged["cascade_minutes"].sum()
        prevented_events = len(flagged)
        total_events = len(cascading)
        total_minutes = cascading["cascade_minutes"].sum()

        pct_events = prevented_events / max(total_events, 1) * 100
        pct_minutes = prevented_minutes / max(total_minutes, 1) * 100
        dollar_savings = prevented_minutes * COST_PER_DELAY_MINUTE

        results_rows.append({
            "k": k,
            "total_cascade_events": total_events,
            "prevented_events": prevented_events,
            "pct_events_prevented": pct_events,
            "total_cascade_minutes": total_minutes,
            "prevented_minutes": prevented_minutes,
            "pct_minutes_prevented": pct_minutes,
            "dollar_savings": dollar_savings,
        })

        print(f"\nAvoiding top {k} risky pairs:")
        print(f"  Cascading events prevented: {prevented_events:,} / {total_events:,} ({pct_events:.1f}%)")
        print(f"  Delay minutes prevented: {prevented_minutes:,.0f} / {total_minutes:,.0f} ({pct_minutes:.1f}%)")
        print(f"  Dollar savings: ${dollar_savings:,.0f}")

    results_df = pd.DataFrame(results_rows)

    # Also compute by month for seasonal breakdown
    monthly_rows = []
    for k in top_k_values:
        for month in range(1, 13):
            month_data = cascading[cascading["month"] == month]
            flagged_month = month_data[month_data[f"flagged_k{k}"]]
            monthly_rows.append({
                "k": k,
                "month": month,
                "total_events": len(month_data),
                "prevented_events": len(flagged_month),
                "prevented_minutes": flagged_month["cascade_minutes"].sum(),
                "dollar_savings": flagged_month["cascade_minutes"].sum() * COST_PER_DELAY_MINUTE,
            })
    monthly_df = pd.DataFrame(monthly_rows)

    # Fix 7: Honest impact scaling
    # Not every flagged pair is actually assigned on every day
    avg_daily_sequences = flights.groupby("date").size().mean() / 2  # inbound+outbound -> sequences
    n_airports = len(set(cascading["airport_in"]) | set(cascading["airport_out"]))
    n_possible_pairs = n_airports * (n_airports - 1) / 2
    assignment_prob = avg_daily_sequences / max(n_possible_pairs, 1)
    print(f"\nAssignment probability scaling: {avg_daily_sequences:.0f} daily sequences / "
          f"{n_possible_pairs:.0f} possible pairs = {assignment_prob:.4f}")

    for i, row in results_df.iterrows():
        results_df.loc[i, "adjusted_savings"] = row["dollar_savings"] * assignment_prob
        results_df.loc[i, "adjusted_prevented_events"] = row["prevented_events"] * assignment_prob

    # Annualize (data spans multiple years)
    years_in_data = flights["Year"].nunique()
    print(f"\nAnnualized estimates (over {years_in_data} years of data):")
    for _, row in results_df.iterrows():
        annual_upper = row["dollar_savings"] / max(years_in_data, 1)
        annual_adjusted = row["adjusted_savings"] / max(years_in_data, 1)
        print(f"  K={int(row['k'])}: ${annual_upper:,.0f}/year (upper bound), "
              f"${annual_adjusted:,.0f}/year (adjusted)")

    # Save results
    results_df.to_parquet(cache_path, index=False)
    monthly_df.to_parquet(SIMULATION_DIR / "monthly_breakdown.parquet", index=False)

    # Save top cascading events for the report
    top_cascades = cascading.groupby(["pair_a", "pair_b"]).agg(
        total_events=("cascade_minutes", "size"),
        total_delay_minutes=("cascade_minutes", "sum"),
        avg_delay=("cascade_minutes", "mean"),
    ).reset_index().sort_values("total_delay_minutes", ascending=False)
    top_cascades.to_parquet(SIMULATION_DIR / "top_cascading_pairs.parquet", index=False)

    print(f"\nTop 10 actual cascading delay pairs:")
    print(top_cascades.head(10).to_string(index=False))

    # Cascade mechanics: compute actual propagated delay per pair
    print("\n\nCASCADE PROPAGATION ANALYSIS")
    print("=" * 60)
    compute_cascade_propagation(flights_df, risk_scores_df)

    return results_df


if __name__ == "__main__":
    from src.data_processing import load_flights

    flights = load_flights()
    risk_scores = pd.read_parquet(MODEL_DIR / "risk_scores.parquet")

    results = run_simulation(flights, risk_scores)
    print(f"\nResults:\n{results.to_string(index=False)}")
