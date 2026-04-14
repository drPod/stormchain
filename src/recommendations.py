"""Generate actionable recommendations: avoid lists, swap suggestions, seasonal summaries."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    PROCESSED_DIR, MODEL_DIR, SIMULATION_DIR, OUTPUT_DIR,
    DFW_IATA, COST_PER_DELAY_MINUTE, AIRPORT_TO_REGION,
)

SEASONS = {
    "Spring (Mar-May)": [3, 4, 5],
    "Summer (Jun-Aug)": [6, 7, 8],
    "Fall (Sep-Nov)": [9, 10, 11],
    "Winter (Dec-Feb)": [12, 1, 2],
}

RISK_THRESHOLD = 65  # risk score above which we flag


def generate_avoid_list(
    risk_scores: pd.DataFrame,
    cascade_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Generate the concrete avoid list: which pairs to not schedule, by season."""
    rows = []

    for season_name, months in SEASONS.items():
        season_scores = risk_scores[risk_scores["month"].isin(months)].copy()

        # Flag by risk score
        flagged = season_scores[season_scores["risk_score"] >= RISK_THRESHOLD].copy()

        # Also flag by cascade cost if available
        if cascade_data is not None:
            cascade_season = cascade_data[cascade_data["month"].isin(months)]
            high_cascade = cascade_season[cascade_season["cascade_cost"] > 10000]
            # Merge to add cascade info
            flagged = flagged.merge(
                high_cascade[["airport_a", "airport_b", "month", "cascade_events",
                              "avg_cascade_minutes", "cascade_cost"]],
                on=["airport_a", "airport_b", "month"],
                how="left",
            )

        for _, row in flagged.iterrows():
            # Determine primary reason
            reasons = []
            if row.get("joint_weather_delay_prob", 0) > 0.05:
                reasons.append("correlated weather delays")
            if row.get("missed_connection_prob", 0) > 0.5:
                reasons.append("tight turnaround / missed connection risk")
            if row.get("duty_violation_risk", 0) > 0.8:
                reasons.append("duty time violation risk")
            if row.get("fatigue_exposure", 0) > 0:
                reasons.append("fatigue / WOCL exposure")
            if row.get("thunderstorm_co_occurrence", 0) > 0.05:
                reasons.append("thunderstorm co-occurrence")
            if not reasons:
                reasons.append("elevated composite risk")

            rows.append({
                "season": season_name,
                "month": row["month"],
                "airport_a": row["airport_a"],
                "airport_b": row["airport_b"],
                "risk_score": row["risk_score"],
                "reason": "; ".join(reasons),
                "cascade_cost": row.get("cascade_cost", 0) or 0,
            })

    avoid_df = pd.DataFrame(rows).sort_values(
        ["season", "risk_score"], ascending=[True, False]
    )

    # Deduplicate: keep highest risk month per pair per season
    avoid_df = avoid_df.sort_values("risk_score", ascending=False).drop_duplicates(
        subset=["season", "airport_a", "airport_b"], keep="first"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    avoid_df.to_parquet(OUTPUT_DIR / "avoid_list.parquet", index=False)
    avoid_df.to_csv(OUTPUT_DIR / "avoid_list.csv", index=False)

    print(f"AVOID LIST: {len(avoid_df)} pair-season recommendations")
    for season in SEASONS:
        n = len(avoid_df[avoid_df["season"] == season])
        print(f"  {season}: {n} pairs to avoid")

    return avoid_df


def generate_swap_recommendations(
    risk_scores: pd.DataFrame,
    avoid_list: pd.DataFrame,
    flights_df: pd.DataFrame,
) -> pd.DataFrame:
    """For each flagged pair, suggest a safe alternative destination."""
    # Get airports that actually have DFW service
    active_dests = set(
        flights_df[flights_df["Origin"] == DFW_IATA]["Dest"].unique()
    )

    swaps = []
    for _, row in avoid_list.iterrows():
        airport_a = row["airport_a"]
        airport_b = row["airport_b"]
        month = row["month"]

        # Find all pairs involving airport_a in this month
        a_pairs = risk_scores[
            (risk_scores["month"] == month) &
            ((risk_scores["airport_a"] == airport_a) | (risk_scores["airport_b"] == airport_a))
        ].copy()

        # Get the "other" airport for each pair
        a_pairs["other"] = np.where(
            a_pairs["airport_a"] == airport_a,
            a_pairs["airport_b"],
            a_pairs["airport_a"],
        )

        # Filter to airports with actual service, exclude the bad pair
        a_pairs = a_pairs[
            (a_pairs["other"].isin(active_dests)) &
            (a_pairs["other"] != airport_b) &
            (a_pairs["risk_score"] < 30)  # Only suggest safe alternatives
        ]

        if len(a_pairs) > 0:
            best = a_pairs.nsmallest(1, "risk_score").iloc[0]
            swaps.append({
                "season": row["season"],
                "avoid_origin": airport_a,
                "avoid_dest": airport_b,
                "avoid_risk": row["risk_score"],
                "swap_dest": best["other"],
                "swap_risk": best["risk_score"],
                "risk_reduction": row["risk_score"] - best["risk_score"],
            })

    swap_df = pd.DataFrame(swaps).sort_values("risk_reduction", ascending=False)
    swap_df.to_csv(OUTPUT_DIR / "swap_recommendations.csv", index=False)

    print(f"\nSWAP RECOMMENDATIONS: {len(swap_df)} alternatives found")
    print("\nTop 10 swaps by risk reduction:")
    for _, row in swap_df.head(10).iterrows():
        print(f"  {row['avoid_origin']}→DFW→{row['avoid_dest']} (risk {row['avoid_risk']:.0f}) "
              f"→ swap to {row['avoid_origin']}→DFW→{row['swap_dest']} (risk {row['swap_risk']:.0f}) "
              f"| reduction: {row['risk_reduction']:.0f} points")

    return swap_df


def generate_seasonal_summary(
    risk_scores: pd.DataFrame,
) -> pd.DataFrame:
    """Produce top-10 pairs per season with geographic patterns."""
    summaries = []

    for season_name, months in SEASONS.items():
        season = risk_scores[risk_scores["month"].isin(months)].copy()

        # Average risk across season months per pair
        pair_avg = season.groupby(["airport_a", "airport_b"]).agg(
            avg_risk=("risk_score", "mean"),
            max_risk=("risk_score", "max"),
            peak_month=("risk_score", "idxmax"),
        ).reset_index().sort_values("avg_risk", ascending=False)

        # Get peak month name
        month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                       7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

        for _, row in pair_avg.head(10).iterrows():
            a_region = AIRPORT_TO_REGION.get(row["airport_a"], "Unknown")
            b_region = AIRPORT_TO_REGION.get(row["airport_b"], "Unknown")

            if a_region == b_region:
                pattern = f"Same region ({a_region})"
            else:
                pattern = f"Cross-region ({a_region} / {b_region})"

            summaries.append({
                "season": season_name,
                "rank": len([s for s in summaries if s["season"] == season_name]) + 1,
                "airport_a": row["airport_a"],
                "airport_b": row["airport_b"],
                "avg_risk": row["avg_risk"],
                "max_risk": row["max_risk"],
                "geographic_pattern": pattern,
            })

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(OUTPUT_DIR / "seasonal_summary.csv", index=False)

    print(f"\nSEASONAL SUMMARY:")
    for season_name in SEASONS:
        season_data = summary_df[summary_df["season"] == season_name]
        print(f"\n  {season_name}:")
        for _, row in season_data.iterrows():
            print(f"    #{int(row['rank'])}. {row['airport_a']}-{row['airport_b']} "
                  f"(avg risk {row['avg_risk']:.0f}, {row['geographic_pattern']})")

    return summary_df


def compute_objective_coverage(
    risk_scores: pd.DataFrame,
    avoid_list: pd.DataFrame,
) -> dict:
    """Map each PDF objective to our model's coverage."""
    avoid_pairs = set(zip(avoid_list["airport_a"], avoid_list["airport_b"]))

    results = {}

    # Objective 1: Delay propagation
    high_delay_pairs = risk_scores[risk_scores["joint_weather_delay_prob"] > 0.05]
    n_high = len(high_delay_pairs[["airport_a","airport_b"]].drop_duplicates())
    n_covered = sum(1 for _, r in high_delay_pairs[["airport_a","airport_b"]].drop_duplicates().iterrows()
                    if (r["airport_a"], r["airport_b"]) in avoid_pairs)
    results["delay_propagation"] = {"total_risky": n_high, "in_avoid_list": n_covered,
                                     "coverage": n_covered / max(n_high, 1) * 100}

    # Objective 2: Duty time violations
    if "duty_violation_risk" in risk_scores.columns:
        duty_risk = risk_scores[risk_scores["duty_violation_risk"] > 0.8]
        n_duty = len(duty_risk[["airport_a","airport_b"]].drop_duplicates())
        n_duty_covered = sum(1 for _, r in duty_risk[["airport_a","airport_b"]].drop_duplicates().iterrows()
                             if (r["airport_a"], r["airport_b"]) in avoid_pairs)
        results["duty_violations"] = {"total_risky": n_duty, "in_avoid_list": n_duty_covered,
                                       "coverage": n_duty_covered / max(n_duty, 1) * 100}

    # Objective 3: Missed connections
    if "missed_connection_prob" in risk_scores.columns:
        missed = risk_scores[risk_scores["missed_connection_prob"] > 0.5]
        n_missed = len(missed[["airport_a","airport_b"]].drop_duplicates())
        n_missed_covered = sum(1 for _, r in missed[["airport_a","airport_b"]].drop_duplicates().iterrows()
                               if (r["airport_a"], r["airport_b"]) in avoid_pairs)
        results["missed_connections"] = {"total_risky": n_missed, "in_avoid_list": n_missed_covered,
                                          "coverage": n_missed_covered / max(n_missed, 1) * 100}

    # Objective 4: Fatigue
    if "fatigue_exposure" in risk_scores.columns:
        fatigue = risk_scores[risk_scores["fatigue_exposure"] > 0]
        n_fatigue = len(fatigue[["airport_a","airport_b"]].drop_duplicates())
        n_fatigue_covered = sum(1 for _, r in fatigue[["airport_a","airport_b"]].drop_duplicates().iterrows()
                                if (r["airport_a"], r["airport_b"]) in avoid_pairs)
        results["fatigue_risk"] = {"total_risky": n_fatigue, "in_avoid_list": n_fatigue_covered,
                                    "coverage": n_fatigue_covered / max(n_fatigue, 1) * 100}

    print(f"\nOBJECTIVE COVERAGE:")
    for obj, stats in results.items():
        print(f"  {obj}: {stats['in_avoid_list']}/{stats['total_risky']} risky pairs in avoid list ({stats['coverage']:.0f}%)")

    return results


if __name__ == "__main__":
    from src.data_processing import load_flights

    risk_scores = pd.read_parquet(MODEL_DIR / "risk_scores.parquet")
    flights = load_flights()

    # Load cascade data if available
    cascade_path = SIMULATION_DIR / "cascade_propagation.parquet"
    cascade_data = pd.read_parquet(cascade_path) if cascade_path.exists() else None

    print("=" * 70)
    print("GENERATING RECOMMENDATIONS")
    print("=" * 70)

    avoid = generate_avoid_list(risk_scores, cascade_data)
    swaps = generate_swap_recommendations(risk_scores, avoid, flights)
    seasonal = generate_seasonal_summary(risk_scores)
    objectives = compute_objective_coverage(risk_scores, avoid)
