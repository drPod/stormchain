"""Case study analysis of the worst cascading delay day: May 28, 2024."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    PROCESSED_DIR, MODEL_DIR, OUTPUT_DIR, FIGURES_DIR,
    DFW_IATA, DELAY_THRESHOLD_MINUTES, COST_PER_DELAY_MINUTE,
    MIN_TURNAROUND_MINUTES,
)

CASE_STUDY_DATE = "2024-05-28"


def run_case_study() -> dict:
    """Analyze May 28, 2024 — the worst cascading delay day in our dataset."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    flights = pd.read_parquet(PROCESSED_DIR / "flights_dfw.parquet")
    flights["FlightDate"] = pd.to_datetime(flights["FlightDate"])
    flights["date"] = flights["FlightDate"].dt.normalize()

    risk_scores = pd.read_parquet(MODEL_DIR / "risk_scores.parquet")

    target_date = pd.Timestamp(CASE_STUDY_DATE)
    day = flights[flights["date"] == target_date]

    inbound = day[day["Dest"] == DFW_IATA].copy()
    outbound = day[day["Origin"] == DFW_IATA].copy()

    print(f"CASE STUDY: {CASE_STUDY_DATE}")
    print(f"=" * 70)
    print(f"Total flights: {len(day)} ({len(inbound)} inbound, {len(outbound)} outbound)")

    # Weather-delayed inbound
    wx_inbound = inbound[inbound["WeatherDelay"] > 0]
    # Delayed outbound
    delayed_outbound = outbound[outbound["DepDelay"] > DELAY_THRESHOLD_MINUTES]

    print(f"\nInbound weather-delayed: {len(wx_inbound)} ({len(wx_inbound)/len(inbound)*100:.1f}%)")
    print(f"  Total weather delay: {wx_inbound['WeatherDelay'].sum():,.0f} minutes")
    print(f"  Avg weather delay: {wx_inbound['WeatherDelay'].mean():.0f} minutes")
    print(f"\nOutbound delayed >15min: {len(delayed_outbound)} ({len(delayed_outbound)/len(outbound)*100:.1f}%)")
    print(f"  Total departure delay: {delayed_outbound['DepDelay'].sum():,.0f} minutes")

    # Build actual sequences that occurred
    # Match each weather-delayed inbound with each delayed outbound
    # where outbound departs after inbound arrives + minimum turnaround
    def hhmm_to_min(t):
        if pd.isna(t):
            return np.nan
        t = int(t)
        return (t // 100) * 60 + (t % 100)

    wx_inbound = wx_inbound.copy()
    wx_inbound["arr_min"] = wx_inbound["CRSArrTime"].apply(hhmm_to_min)
    delayed_outbound = delayed_outbound.copy()
    delayed_outbound["dep_min"] = delayed_outbound["CRSDepTime"].apply(hhmm_to_min)

    # Build realistic cascading sequences
    # Each inbound flight has ONE pilot who flies ONE outbound — the next
    # available departure after arrival + minimum turnaround.
    # Sort outbound by departure time and greedily assign each inbound
    # to its earliest feasible outbound (each outbound used at most once).
    delayed_outbound = delayed_outbound.sort_values("dep_min")
    used_outbound = set()

    cascades = []
    for _, inf in wx_inbound.sort_values("arr_min").iterrows():
        if pd.isna(inf["arr_min"]):
            continue

        # Find first available outbound after turnaround
        best_outf = None
        for idx, outf in delayed_outbound.iterrows():
            if idx in used_outbound:
                continue
            if pd.isna(outf["dep_min"]):
                continue
            gap = outf["dep_min"] - inf["arr_min"]
            if gap >= MIN_TURNAROUND_MINUTES:
                best_outf = outf
                used_outbound.add(idx)
                break

        if best_outf is None:
            continue

        outf = best_outf
        gap = outf["dep_min"] - inf["arr_min"]
        origin = inf["Origin"]
        dest = outf["Dest"]
        if origin == dest:
            continue

        # Cascade computation
        actual_arr_delay = inf.get("ArrDelay", 0) or 0
        propagated = max(0, actual_arr_delay - gap)
        outbound_delay = outf.get("DepDelay", 0) or 0
        total_cascade = propagated + outbound_delay

        # Check if this pair is in our risk model
        pair_a = min(origin, dest)
        pair_b = max(origin, dest)
        month = target_date.month

        pair_risk = risk_scores[
            (risk_scores["airport_a"] == pair_a) &
            (risk_scores["airport_b"] == pair_b) &
            (risk_scores["month"] == month)
        ]
        risk_score = pair_risk["risk_score"].values[0] if len(pair_risk) > 0 else 0

        cascades.append({
            "origin": origin,
            "dest": dest,
            "inbound_weather_delay": inf["WeatherDelay"],
            "inbound_arr_delay": actual_arr_delay,
            "turnaround_gap": gap,
            "propagated_delay": propagated,
            "outbound_dep_delay": outbound_delay,
            "total_cascade_minutes": total_cascade,
            "risk_score": risk_score,
            "inbound_arr_time": inf["arr_min"],
            "outbound_dep_time": outf["dep_min"],
        })

    cascade_df = pd.DataFrame(cascades)
    print(f"\nCascading sequences identified: {len(cascade_df):,}")
    print(f"  With propagated delay > 0: {(cascade_df['propagated_delay'] > 0).sum():,}")
    print(f"  Total cascade minutes: {cascade_df['total_cascade_minutes'].sum():,.0f}")
    print(f"  Total cascade cost: ${cascade_df['total_cascade_minutes'].sum() * COST_PER_DELAY_MINUTE:,.0f}")

    # How many would our model have flagged?
    for k in [50, 100, 200, 500]:
        top_k = risk_scores.nlargest(k, "risk_score")["risk_score"].min()
        flagged = cascade_df[cascade_df["risk_score"] >= top_k]
        flagged_minutes = flagged["total_cascade_minutes"].sum()
        total_minutes = cascade_df["total_cascade_minutes"].sum()
        pct = flagged_minutes / max(total_minutes, 1) * 100

        print(f"\n  Top {k} risky pairs: flagged {len(flagged):,} / {len(cascade_df):,} sequences")
        print(f"    Cascade minutes flagged: {flagged_minutes:,.0f} / {total_minutes:,.0f} ({pct:.1f}%)")
        print(f"    Savings: ${flagged_minutes * COST_PER_DELAY_MINUTE:,.0f}")

    # Top cascading origin-dest pairs this day
    print(f"\nTop 10 cascading pairs on {CASE_STUDY_DATE}:")
    pair_summary = cascade_df.groupby(["origin", "dest"]).agg(
        n_sequences=("total_cascade_minutes", "size"),
        total_cascade=("total_cascade_minutes", "sum"),
        avg_cascade=("total_cascade_minutes", "mean"),
        risk_score=("risk_score", "mean"),
    ).sort_values("total_cascade", ascending=False)
    print(pair_summary.head(10).to_string())

    # Timeline: when did the worst delays happen?
    print(f"\nDelay timeline (by hour of inbound arrival):")
    cascade_df["arr_hour"] = (cascade_df["inbound_arr_time"] // 60).astype(int)
    hourly = cascade_df.groupby("arr_hour").agg(
        n_cascades=("total_cascade_minutes", "size"),
        total_delay=("total_cascade_minutes", "sum"),
    )
    for hour, row in hourly.iterrows():
        bar = "#" * min(50, int(row["total_delay"] / 5000))
        print(f"  {int(hour):02d}:00  {int(row['n_cascades']):5d} cascades  {row['total_delay']:10,.0f} min  {bar}")

    # Save for report
    cascade_df.to_parquet(OUTPUT_DIR / "case_study_cascades.parquet", index=False)
    pair_summary.to_parquet(OUTPUT_DIR / "case_study_pair_summary.parquet", index=False)

    return {
        "date": CASE_STUDY_DATE,
        "total_flights": len(day),
        "weather_delayed_inbound": len(wx_inbound),
        "delayed_outbound": len(delayed_outbound),
        "cascading_sequences": len(cascade_df),
        "total_cascade_minutes": cascade_df["total_cascade_minutes"].sum(),
        "total_cost": cascade_df["total_cascade_minutes"].sum() * COST_PER_DELAY_MINUTE,
    }


if __name__ == "__main__":
    results = run_case_study()
    print(f"\nSummary: {results}")
