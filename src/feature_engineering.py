"""Feature engineering for airport pairs and sequences."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    PROCESSED_DIR, REFERENCE_DIR, DFW_IATA,
    DELAY_THRESHOLD_MINUTES, FAA_MAX_DUTY_HOURS,
    WOCL_START_HOUR, WOCL_END_HOUR,
    TORNADO_ALLEY, GULF_COAST_HURRICANE, NORTHEAST_WINTER_STORM,
    AIRPORT_TO_REGION,
)


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles."""
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def compute_airport_monthly_stats(flights_df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-airport, per-month delay and flight statistics."""
    cache_path = PROCESSED_DIR / "airport_monthly_stats.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    # Create a row per airport per flight (some flights have DFW on both sides)
    rows = []
    for _, row in []:  # We'll use vectorized approach instead
        pass

    # For inbound flights (Dest=DFW), the "other" airport is Origin
    inbound = flights_df[flights_df["Dest"] == DFW_IATA].copy()
    inbound["airport"] = inbound["Origin"]
    inbound["delay"] = inbound["ArrDelay"]
    inbound["weather_delay"] = inbound["WeatherDelay"]
    inbound["late_aircraft_delay"] = inbound["LateAircraftDelay"]

    # For outbound flights (Origin=DFW), the "other" airport is Dest
    outbound = flights_df[flights_df["Origin"] == DFW_IATA].copy()
    outbound["airport"] = outbound["Dest"]
    outbound["delay"] = outbound["DepDelay"]
    outbound["weather_delay"] = outbound["WeatherDelay"]
    outbound["late_aircraft_delay"] = outbound["LateAircraftDelay"]

    combined = pd.concat([
        inbound[["airport", "Month", "Year", "FlightDate", "delay", "weather_delay",
                 "late_aircraft_delay", "DepDelay", "ArrDelay", "Cancelled"]],
        outbound[["airport", "Month", "Year", "FlightDate", "delay", "weather_delay",
                  "late_aircraft_delay", "DepDelay", "ArrDelay", "Cancelled"]],
    ], ignore_index=True)

    stats = combined.groupby(["airport", "Month"]).agg(
        flight_count=("delay", "size"),
        weather_delay_rate=("weather_delay", lambda x: (x > 0).mean()),
        weather_delay_mean=("weather_delay", "mean"),
        weather_delay_p90=("weather_delay", lambda x: x.quantile(0.9)),
        avg_delay=("delay", "mean"),
        delay_rate_15=("delay", lambda x: (x > DELAY_THRESHOLD_MINUTES).mean()),
        delay_std=("delay", "std"),
        cancellation_rate=("Cancelled", "mean"),
        late_aircraft_rate=("late_aircraft_delay", lambda x: (x > 0).mean()),
    ).reset_index()

    stats.to_parquet(cache_path, index=False)
    print(f"Saved airport monthly stats ({len(stats):,} rows) to {cache_path}")
    return stats


def compute_airport_monthly_weather(daily_weather_df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-airport, per-month weather statistics."""
    cache_path = PROCESSED_DIR / "airport_monthly_weather.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    daily_weather_df["month"] = pd.to_datetime(daily_weather_df["date"]).dt.month

    stats = daily_weather_df.groupby(["airport", "month"]).agg(
        precip_days=("precip_total", lambda x: (x > 0.1).sum()),  # >0.1 inches
        heavy_precip_days=("precip_total", lambda x: (x > 1.0).sum()),  # >1 inch
        thunderstorm_days=("thunderstorm_hours", lambda x: (x > 0).sum()),
        fog_days=("fog_hours", lambda x: (x > 0).sum()),
        snow_days=("snowfall_total", lambda x: (x > 0).sum()),
        high_wind_days=("high_wind_hours", lambda x: (x > 0).sum()),
        severe_weather_days=("severe_weather_hours", lambda x: (x > 0).sum()),
        avg_precip=("precip_total", "mean"),
        avg_wind_speed=("wind_speed_mean", "mean"),
        avg_wind_gusts=("wind_gusts_max", "mean"),
        avg_cloud_cover=("cloud_cover_mean", "mean"),
        pressure_volatility=("pressure_std", "mean"),
        thunderstorm_hours_total=("thunderstorm_hours", "sum"),
        severe_hours_total=("severe_weather_hours", "sum"),
    ).reset_index()

    stats.to_parquet(cache_path, index=False)
    print(f"Saved airport monthly weather ({len(stats):,} rows) to {cache_path}")
    return stats


def compute_pair_features(
    flights_df: pd.DataFrame,
    daily_weather_df: pd.DataFrame,
    airports_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute features for each airport pair (A, B) by month — vectorized."""
    cache_path = PROCESSED_DIR / "airport_pairs.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    # Limit to top airports by flight volume to keep computation tractable
    flights_df = flights_df.copy()
    flights_df["date"] = flights_df["FlightDate"].dt.normalize()
    flights_df["other_airport"] = np.where(
        flights_df["Origin"] == DFW_IATA, flights_df["Dest"], flights_df["Origin"]
    )

    # Top airports by flight volume (keeps pair count manageable)
    top_airports = (
        flights_df["other_airport"]
        .value_counts()
        .head(80)
        .index.tolist()
    )
    print(f"Computing pair features for top {len(top_airports)} airports ...")

    # Daily delay indicators per airport
    daily_delays = flights_df.groupby(["other_airport", "date"]).agg(
        has_weather_delay=("WeatherDelay", lambda x: (x > 0).any()),
        has_delay_15=("DepDelay", lambda x: (x > DELAY_THRESHOLD_MINUTES).any()),
        max_weather_delay=("WeatherDelay", "max"),
    ).reset_index()
    daily_delays["month"] = daily_delays["date"].dt.month

    # Pivot to create airport x date matrices
    weather_delay_pivot = daily_delays.pivot_table(
        values="has_weather_delay", index="date", columns="other_airport", aggfunc="max"
    ).fillna(False)
    delay_15_pivot = daily_delays.pivot_table(
        values="has_delay_15", index="date", columns="other_airport", aggfunc="max"
    ).fillna(False)

    # Prepare daily weather
    daily_weather_df = daily_weather_df.copy()
    daily_weather_df["date"] = pd.to_datetime(daily_weather_df["date"])
    daily_weather_df["month"] = daily_weather_df["date"].dt.month

    # Pivot weather variables
    precip_pivot = daily_weather_df.pivot_table(
        values="precip_total", index="date", columns="airport", aggfunc="mean"
    )
    wind_pivot = daily_weather_df.pivot_table(
        values="wind_gusts_max", index="date", columns="airport", aggfunc="mean"
    )
    ts_pivot = daily_weather_df.pivot_table(
        values="thunderstorm_hours", index="date", columns="airport", aggfunc="sum"
    ).fillna(0)
    severe_pivot = daily_weather_df.pivot_table(
        values="severe_weather_hours", index="date", columns="airport", aggfunc="sum"
    ).fillna(0)

    # IFR conditions pivot — use METAR data if available, fall back to Open-Meteo proxy
    metar_path = PROCESSED_DIR / "metar_daily.parquet"
    if metar_path.exists():
        print("  Using real METAR data for IFR features")
        metar_daily = pd.read_parquet(metar_path)
        metar_daily["date"] = pd.to_datetime(metar_daily["date"])
        ifr_pivot = metar_daily.pivot_table(
            values="metar_ifr_hours", index="date", columns="airport", aggfunc="sum"
        ).fillna(0)
        # Also create METAR thunderstorm pivot for better accuracy
        metar_ts_pivot = metar_daily.pivot_table(
            values="metar_thunderstorm_hours", index="date", columns="airport", aggfunc="sum"
        ).fillna(0)
        metar_low_vis_pivot = metar_daily.pivot_table(
            values="metar_low_vis_hours", index="date", columns="airport", aggfunc="sum"
        ).fillna(0)
    else:
        print("  METAR not available, using Open-Meteo IFR proxy")
        ifr_pivot = daily_weather_df.pivot_table(
            values="ifr_hours", index="date", columns="airport", aggfunc="sum"
        ).fillna(0) if "ifr_hours" in daily_weather_df.columns else pd.DataFrame()
        metar_ts_pivot = pd.DataFrame()
        metar_low_vis_pivot = pd.DataFrame()

    # Compute missed connection data: per-airport delay distributions
    inbound_delays = flights_df[flights_df["Dest"] == DFW_IATA].groupby("other_airport")["ArrDelay"].agg(
        delay_p90=lambda x: x.dropna().quantile(0.9),
        delay_p75=lambda x: x.dropna().quantile(0.75),
        delay_median=lambda x: x.dropna().median(),
    ).to_dict("index")

    # Compute typical turnaround and flight times per airport pair
    inbound_times = flights_df[flights_df["Dest"] == DFW_IATA].groupby("Origin").agg(
        avg_airtime=("AirTime", "mean"),
        avg_crs_arr=("CRSArrTime", "median"),
    ).to_dict("index")
    outbound_times = flights_df[flights_df["Origin"] == DFW_IATA].groupby("Dest").agg(
        avg_airtime=("AirTime", "mean"),
        avg_crs_dep=("CRSDepTime", "median"),
    ).to_dict("index")

    # Airport coordinates
    airport_coords = airports_df.set_index("iata")[["latitude", "longitude"]].to_dict("index")

    pair_rows = []
    pair_count = 0
    total_pairs = len(top_airports) * (len(top_airports) - 1) // 2

    for i, a in enumerate(top_airports):
        for b in top_airports[i + 1:]:
            pair_count += 1
            if pair_count % 200 == 0:
                print(f"  Pair {pair_count}/{total_pairs} ...")

            for month in range(1, 13):
                # Get dates for this month
                month_dates = weather_delay_pivot.index[weather_delay_pivot.index.month == month]

                # Joint delay features
                if a in weather_delay_pivot.columns and b in weather_delay_pivot.columns:
                    a_wd = weather_delay_pivot.loc[month_dates, a] if a in weather_delay_pivot.columns else pd.Series(dtype=bool)
                    b_wd = weather_delay_pivot.loc[month_dates, b] if b in weather_delay_pivot.columns else pd.Series(dtype=bool)

                    # Only use dates where both airports have data
                    valid = a_wd.notna() & b_wd.notna()
                    n_overlap = valid.sum()
                    if n_overlap < 5:
                        continue

                    a_wd_v = a_wd[valid].astype(bool)
                    b_wd_v = b_wd[valid].astype(bool)

                    both_weather = (a_wd_v & b_wd_v).mean()
                    cond_delay = b_wd_v[a_wd_v].mean() if a_wd_v.sum() > 0 else 0

                    a_d15 = delay_15_pivot.loc[month_dates, a][valid].astype(bool) if a in delay_15_pivot.columns else pd.Series(dtype=bool)
                    b_d15 = delay_15_pivot.loc[month_dates, b][valid].astype(bool) if b in delay_15_pivot.columns else pd.Series(dtype=bool)
                    both_delay_15 = (a_d15 & b_d15).mean() if len(a_d15) > 0 and len(b_d15) > 0 else 0
                else:
                    both_weather = both_delay_15 = cond_delay = 0
                    n_overlap = 0

                # Weather correlations
                precip_corr = wind_corr = ts_co = severe_co = 0
                if a in precip_pivot.columns and b in precip_pivot.columns:
                    wx_month_dates = month_dates.intersection(precip_pivot.index)
                    month_precip = precip_pivot.loc[wx_month_dates] if len(wx_month_dates) > 0 else precip_pivot.iloc[:0]
                    a_p = month_precip[a].dropna()
                    b_p = month_precip[b].dropna()
                    common = a_p.index.intersection(b_p.index)
                    if len(common) > 5:
                        precip_corr = a_p.loc[common].corr(b_p.loc[common])
                        if np.isnan(precip_corr):
                            precip_corr = 0

                if a in wind_pivot.columns and b in wind_pivot.columns:
                    wx_month_dates2 = month_dates.intersection(wind_pivot.index)
                    month_wind = wind_pivot.loc[wx_month_dates2] if len(wx_month_dates2) > 0 else wind_pivot.iloc[:0]
                    a_w = month_wind[a].dropna()
                    b_w = month_wind[b].dropna()
                    common = a_w.index.intersection(b_w.index)
                    if len(common) > 5:
                        wind_corr = a_w.loc[common].corr(b_w.loc[common])
                        if np.isnan(wind_corr):
                            wind_corr = 0

                if a in ts_pivot.columns and b in ts_pivot.columns:
                    wx_month_dates3 = month_dates.intersection(ts_pivot.index)
                    month_ts = ts_pivot.loc[wx_month_dates3] if len(wx_month_dates3) > 0 else ts_pivot.iloc[:0]
                    ts_co = ((month_ts[a] > 0) & (month_ts[b] > 0)).mean()

                if a in severe_pivot.columns and b in severe_pivot.columns:
                    wx_month_dates4 = month_dates.intersection(severe_pivot.index)
                    month_sv = severe_pivot.loc[wx_month_dates4] if len(wx_month_dates4) > 0 else severe_pivot.iloc[:0]
                    severe_co = ((month_sv[a] > 0) & (month_sv[b] > 0)).mean()

                # IFR co-occurrence (from real METAR if available)
                ifr_co = 0
                metar_ts_co = 0
                metar_low_vis_co = 0
                if len(ifr_pivot) > 0 and a in ifr_pivot.columns and b in ifr_pivot.columns:
                    wx_ifr_dates = month_dates.intersection(ifr_pivot.index)
                    if len(wx_ifr_dates) > 0:
                        month_ifr = ifr_pivot.loc[wx_ifr_dates]
                        ifr_co = ((month_ifr[a] > 0) & (month_ifr[b] > 0)).mean()

                if len(metar_ts_pivot) > 0 and a in metar_ts_pivot.columns and b in metar_ts_pivot.columns:
                    wx_mts_dates = month_dates.intersection(metar_ts_pivot.index)
                    if len(wx_mts_dates) > 0:
                        month_mts = metar_ts_pivot.loc[wx_mts_dates]
                        metar_ts_co = ((month_mts[a] > 0) & (month_mts[b] > 0)).mean()

                if len(metar_low_vis_pivot) > 0 and a in metar_low_vis_pivot.columns and b in metar_low_vis_pivot.columns:
                    wx_mlv_dates = month_dates.intersection(metar_low_vis_pivot.index)
                    if len(wx_mlv_dates) > 0:
                        month_mlv = metar_low_vis_pivot.loc[wx_mlv_dates]
                        metar_low_vis_co = ((month_mlv[a] > 0) & (month_mlv[b] > 0)).mean()

                # Fix 3: Missed connection probability
                a_delay_info = inbound_delays.get(a, {})
                b_delay_info = inbound_delays.get(b, {})
                a_in_times = inbound_times.get(a, {})
                b_out_times = outbound_times.get(b, {})

                # Typical turnaround: outbound dep - inbound arr (in minutes)
                a_arr = a_in_times.get("avg_crs_arr", 1200)
                b_dep = b_out_times.get("avg_crs_dep", 1400)
                def hhmm_to_min(t):
                    t = int(t) if not np.isnan(t) else 1200
                    return (t // 100) * 60 + (t % 100)
                turnaround = hhmm_to_min(b_dep) - hhmm_to_min(a_arr)
                if turnaround < 0:
                    turnaround += 1440  # next day

                a_p90 = a_delay_info.get("delay_p90", 30)
                missed_conn_prob = 1.0 if (a_p90 or 0) > turnaround else max(0, (a_p90 or 0) / max(turnaround, 1))
                buffer_adequacy = turnaround / max(a_p90 or 30, 1)

                # Fix 1: Duty time violation risk
                a_airtime = a_in_times.get("avg_airtime", 120) or 120
                b_airtime = b_out_times.get("avg_airtime", 120) or 120
                total_duty_hours = (a_airtime + turnaround + b_airtime + (a_delay_info.get("delay_median", 0) or 0)) / 60
                duty_violation_risk = max(0, total_duty_hours / FAA_MAX_DUTY_HOURS)

                # Fix 2: Fatigue / WOCL exposure
                arr_hour = hhmm_to_min(a_arr) / 60
                dep_hour = hhmm_to_min(b_dep) / 60
                wocl_overlap = 0
                for h in [arr_hour, dep_hour]:
                    if WOCL_START_HOUR <= h <= WOCL_END_HOUR:
                        wocl_overlap += 1
                fatigue_exposure = wocl_overlap / 2  # 0, 0.5, or 1.0

                # Geographic features
                a_c = airport_coords.get(a)
                b_c = airport_coords.get(b)
                if a_c and b_c:
                    dist = haversine(a_c["latitude"], a_c["longitude"],
                                     b_c["latitude"], b_c["longitude"])
                    lat_diff = abs(a_c["latitude"] - b_c["latitude"])
                    lon_diff = abs(a_c["longitude"] - b_c["longitude"])
                else:
                    dist = lat_diff = lon_diff = np.nan

                pair_rows.append({
                    "airport_a": a,
                    "airport_b": b,
                    "month": month,
                    "joint_weather_delay_prob": both_weather,
                    "joint_delay_15_prob": both_delay_15,
                    "conditional_delay_prob": cond_delay,
                    "precip_correlation": precip_corr,
                    "wind_correlation": wind_corr,
                    "thunderstorm_co_occurrence": ts_co,
                    "severe_weather_co_occurrence": severe_co,
                    "distance_ab": dist,
                    "latitude_diff": lat_diff,
                    "longitude_diff": lon_diff,
                    "same_region": int(AIRPORT_TO_REGION.get(a) == AIRPORT_TO_REGION.get(b)),
                    "tornado_alley_pair": int(a in TORNADO_ALLEY and b in TORNADO_ALLEY),
                    "hurricane_pair": int(a in GULF_COAST_HURRICANE and b in GULF_COAST_HURRICANE),
                    "winter_storm_pair": int(a in NORTHEAST_WINTER_STORM and b in NORTHEAST_WINTER_STORM),
                    "month_sin": np.sin(2 * np.pi * month / 12),
                    "month_cos": np.cos(2 * np.pi * month / 12),
                    "n_overlap_days": int(n_overlap),
                    # New features (methodology fixes)
                    "ifr_co_occurrence": ifr_co,
                    "metar_thunderstorm_co": metar_ts_co,
                    "metar_low_vis_co": metar_low_vis_co,
                    "missed_connection_prob": missed_conn_prob,
                    "buffer_adequacy": buffer_adequacy,
                    "duty_violation_risk": duty_violation_risk,
                    "fatigue_exposure": fatigue_exposure,
                    "turnaround_minutes": turnaround,
                })

    pairs_df = pd.DataFrame(pair_rows)
    print(f"Generated {len(pairs_df):,} pair-month features")

    # Merge in airport-level stats
    airport_stats = compute_airport_monthly_stats(flights_df)
    for suffix, col in [("a", "airport_a"), ("b", "airport_b")]:
        stats_renamed = airport_stats.rename(columns={
            c: f"{c}_{suffix}" for c in airport_stats.columns
            if c not in ("airport", "Month")
        })
        stats_renamed = stats_renamed.rename(columns={"airport": col, "Month": "month"})
        pairs_df = pairs_df.merge(stats_renamed, on=[col, "month"], how="left")

    # Interaction features
    if "weather_delay_rate_a" in pairs_df.columns and "weather_delay_rate_b" in pairs_df.columns:
        pairs_df["combined_weather_risk"] = pairs_df["weather_delay_rate_a"] * pairs_df["weather_delay_rate_b"]
        pairs_df["max_weather_risk"] = pairs_df[["weather_delay_rate_a", "weather_delay_rate_b"]].max(axis=1)

    pairs_df.to_parquet(cache_path, index=False)
    print(f"Saved {len(pairs_df):,} airport pair features to {cache_path}")
    return pairs_df


def enrich_sequences_with_features(
    sequences_df: pd.DataFrame,
    pairs_df: pd.DataFrame,
    daily_weather_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add pair-level and weather features to sequence-level data for ML."""
    cache_path = PROCESSED_DIR / "sequences_enriched.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    # Normalize pair keys so (A,B) matches regardless of order
    sequences_df = sequences_df.copy()
    sequences_df["pair_key_a"] = sequences_df[["airport_a", "airport_b"]].min(axis=1)
    sequences_df["pair_key_b"] = sequences_df[["airport_a", "airport_b"]].max(axis=1)

    pairs_df = pairs_df.copy()
    pairs_df["pair_key_a"] = pairs_df["airport_a"]
    pairs_df["pair_key_b"] = pairs_df["airport_b"]

    # Merge pair features
    enriched = sequences_df.merge(
        pairs_df,
        left_on=["pair_key_a", "pair_key_b", "month"],
        right_on=["pair_key_a", "pair_key_b", "month"],
        how="left",
        suffixes=("", "_pair"),
    )

    # Add weather at airports A, B, and DFW on the day of the sequence
    daily_weather_df["date"] = pd.to_datetime(daily_weather_df["date"])
    enriched["date"] = pd.to_datetime(enriched["date"])

    for airport_col, prefix in [("airport_a", "wx_a_"), ("airport_b", "wx_b_")]:
        wx = daily_weather_df.rename(columns={
            c: f"{prefix}{c}" for c in daily_weather_df.columns
            if c not in ("airport", "date")
        })
        wx = wx.rename(columns={"airport": airport_col})
        enriched = enriched.merge(wx, on=[airport_col, "date"], how="left")

    # DFW weather
    dfw_wx = daily_weather_df[daily_weather_df["airport"] == DFW_IATA].copy()
    dfw_cols = {c: f"wx_dfw_{c}" for c in dfw_wx.columns if c not in ("airport", "date")}
    dfw_wx = dfw_wx.rename(columns=dfw_cols).drop(columns=["airport"])
    enriched = enriched.merge(dfw_wx, on="date", how="left")

    # Cyclical time features
    enriched["hour_sin"] = np.sin(2 * np.pi * enriched["inbound_arr_time"] / 1440)
    enriched["hour_cos"] = np.cos(2 * np.pi * enriched["inbound_arr_time"] / 1440)
    enriched["dow_sin"] = np.sin(2 * np.pi * enriched["day_of_week"] / 7)
    enriched["dow_cos"] = np.cos(2 * np.pi * enriched["day_of_week"] / 7)

    enriched.to_parquet(cache_path, index=False)
    print(f"Saved enriched sequences ({len(enriched):,} rows) to {cache_path}")
    return enriched


if __name__ == "__main__":
    from src.data_processing import load_flights, load_weather, compute_daily_weather, load_airports

    flights = load_flights()
    weather = load_weather()
    daily_weather = compute_daily_weather(weather)
    airports = load_airports()

    print("Computing airport monthly stats ...")
    stats = compute_airport_monthly_stats(flights)
    print(f"Stats: {stats.shape}")

    print("\nComputing airport monthly weather ...")
    wx_stats = compute_airport_monthly_weather(daily_weather)
    print(f"Weather stats: {wx_stats.shape}")

    print("\nComputing pair features ...")
    pairs = compute_pair_features(flights, daily_weather, airports)
    print(f"Pairs: {pairs.shape}")
