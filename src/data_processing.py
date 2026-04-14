"""Clean, merge, and prepare flight + weather data for feature engineering."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    PROCESSED_DIR, REFERENCE_DIR, DFW_IATA,
    DELAY_THRESHOLD_MINUTES, MIN_TURNAROUND_MINUTES,
)


def load_flights() -> pd.DataFrame:
    """Load processed DFW flights."""
    path = PROCESSED_DIR / "flights_dfw.parquet"
    df = pd.read_parquet(path)
    df["FlightDate"] = pd.to_datetime(df["FlightDate"], errors="coerce")
    return df


def load_weather() -> pd.DataFrame:
    """Load processed hourly weather."""
    path = PROCESSED_DIR / "weather_hourly.parquet"
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"])
    return df


def load_airports() -> pd.DataFrame:
    """Load airport reference data."""
    return pd.read_csv(REFERENCE_DIR / "airports.csv")


def compute_daily_weather(weather_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly weather to daily summaries per airport."""
    cache_path = PROCESSED_DIR / "weather_daily.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    weather_df["date"] = weather_df["time"].dt.date
    weather_df["date"] = pd.to_datetime(weather_df["date"])
    weather_df["hour"] = weather_df["time"].dt.hour

    agg = weather_df.groupby(["airport", "date"]).agg(
        # Temperature
        temp_mean=("temperature_2m", "mean"),
        temp_min=("temperature_2m", "min"),
        temp_max=("temperature_2m", "max"),
        # Precipitation
        precip_total=("precipitation", "sum"),
        rain_total=("rain", "sum"),
        snowfall_total=("snowfall", "sum"),
        snow_depth_max=("snow_depth", "max"),
        # Wind
        wind_speed_mean=("wind_speed_10m", "mean"),
        wind_speed_max=("wind_speed_10m", "max"),
        wind_gusts_max=("wind_gusts_10m", "max"),
        # Cloud cover
        cloud_cover_mean=("cloud_cover", "mean"),
        cloud_cover_low_mean=("cloud_cover_low", "mean"),
        # Humidity / dewpoint
        humidity_mean=("relative_humidity_2m", "mean"),
        dewpoint_mean=("dew_point_2m", "mean"),
        # Pressure
        pressure_mean=("surface_pressure", "mean"),
        pressure_std=("surface_pressure", "std"),
        # Severe weather counts (hours with specific conditions)
        thunderstorm_hours=("weather_code", lambda x: (x.isin([95, 96, 99])).sum()),
        fog_hours=("weather_code", lambda x: (x.isin([45, 48])).sum()),
        freezing_rain_hours=("weather_code", lambda x: (x.isin([66, 67])).sum()),
        heavy_rain_hours=("weather_code", lambda x: (x.isin([63, 65])).sum()),
        heavy_snow_hours=("weather_code", lambda x: (x.isin([73, 75])).sum()),
        severe_weather_hours=("weather_code", lambda x: (x.isin([45, 48, 63, 65, 66, 67, 73, 75, 95, 96, 99])).sum()),
        # High wind hours
        high_wind_hours=("wind_gusts_10m", lambda x: (x > 35).sum()),
    ).reset_index()

    # Aviation-specific derived features (IFR proxies)
    aviation = weather_df.groupby(["airport", "date"]).apply(
        lambda g: pd.Series({
            # IFR conditions: low ceiling AND (precip OR poor visibility)
            "ifr_hours": ((g["cloud_cover_low"] > 90) & (
                (g["precipitation"] > 0) | ((g["temperature_2m"] - g["dew_point_2m"]).abs() < 3)
            )).sum(),
            # Low ceiling alone
            "low_ceiling_hours": (g["cloud_cover_low"] > 90).sum(),
            # Poor visibility proxy
            "poor_visibility_hours": (
                ((g["temperature_2m"] - g["dew_point_2m"]).abs() < 3) & (g["precipitation"] > 0)
            ).sum(),
        }),
        include_groups=False,
    ).reset_index()
    agg = agg.merge(aviation, on=["airport", "date"], how="left")

    # Derived features
    agg["fog_proxy_hours"] = weather_df.groupby(["airport", "date"]).apply(
        lambda g: ((g["temperature_2m"] - g["dew_point_2m"]).abs() < 3).sum(),
        include_groups=False,
    ).reset_index(drop=True)

    agg.to_parquet(cache_path, index=False)
    print(f"Saved daily weather ({len(agg):,} rows) to {cache_path}")
    return agg


def merge_flights_with_daily_weather(
    flights_df: pd.DataFrame,
    daily_weather_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge each flight with daily weather at both origin and destination."""
    cache_path = PROCESSED_DIR / "flights_weather.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    flights_df["date"] = flights_df["FlightDate"].dt.normalize()

    # Identify the non-DFW airport for each flight
    flights_df["other_airport"] = np.where(
        flights_df["Origin"] == DFW_IATA,
        flights_df["Dest"],
        flights_df["Origin"],
    )
    flights_df["direction"] = np.where(
        flights_df["Dest"] == DFW_IATA, "inbound", "outbound"
    )

    # Merge weather at DFW
    dfw_weather = daily_weather_df[daily_weather_df["airport"] == DFW_IATA].copy()
    dfw_cols = {c: f"dfw_{c}" for c in dfw_weather.columns if c not in ("airport", "date")}
    dfw_weather = dfw_weather.rename(columns=dfw_cols).drop(columns=["airport"])

    merged = flights_df.merge(dfw_weather, on="date", how="left")

    # Merge weather at the other airport
    other_weather = daily_weather_df.copy()
    other_cols = {c: f"other_{c}" for c in other_weather.columns if c not in ("airport", "date")}
    other_weather = other_weather.rename(columns=other_cols)
    other_weather = other_weather.rename(columns={"airport": "other_airport"})

    merged = merged.merge(other_weather, on=["other_airport", "date"], how="left")

    merged.to_parquet(cache_path, index=False)
    print(f"Saved merged flights+weather ({len(merged):,} rows) to {cache_path}")
    return merged


def build_synthetic_sequences(flights_df: pd.DataFrame) -> pd.DataFrame:
    """Build synthetic A->DFW->B sequences from same-day inbound/outbound flights.

    For each day, pairs each inbound flight (arriving DFW) with each outbound
    flight (departing DFW) that departs at least MIN_TURNAROUND_MINUTES later.
    """
    cache_path = PROCESSED_DIR / "sequences.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    # Separate inbound (Dest=DFW) and outbound (Origin=DFW)
    inbound = flights_df[flights_df["Dest"] == DFW_IATA].copy()
    outbound = flights_df[flights_df["Origin"] == DFW_IATA].copy()

    # Need CRSArrTime for inbound and CRSDepTime for outbound
    inbound = inbound.dropna(subset=["CRSArrTime"])
    outbound = outbound.dropna(subset=["CRSDepTime"])

    # Convert HHMM times to minutes since midnight
    def hhmm_to_minutes(t):
        t = int(t)
        return (t // 100) * 60 + (t % 100)

    inbound["arr_minutes"] = inbound["CRSArrTime"].apply(hhmm_to_minutes)
    outbound["dep_minutes"] = outbound["CRSDepTime"].apply(hhmm_to_minutes)

    # Sample to keep tractable — for each date, take up to 50 inbound and 50 outbound
    sequences = []
    dates = flights_df["FlightDate"].dt.date.unique()
    total_dates = len(dates)

    for i, date in enumerate(dates):
        if (i + 1) % 100 == 0:
            print(f"  Building sequences: {i+1}/{total_dates} dates ...")

        date_ts = pd.Timestamp(date)
        day_in = inbound[inbound["FlightDate"].dt.date == date]
        day_out = outbound[outbound["FlightDate"].dt.date == date]

        if len(day_in) == 0 or len(day_out) == 0:
            continue

        # Sample if too many
        if len(day_in) > 50:
            day_in = day_in.sample(50, random_state=42)
        if len(day_out) > 50:
            day_out = day_out.sample(50, random_state=42)

        for _, inf in day_in.iterrows():
            for _, outf in day_out.iterrows():
                gap = outf["dep_minutes"] - inf["arr_minutes"]
                if gap < MIN_TURNAROUND_MINUTES:
                    continue

                # Same airport = no sequence (A->DFW->A is unusual)
                airport_a = inf["Origin"]
                airport_b = outf["Dest"]
                if airport_a == airport_b:
                    continue

                # Label: cascading delay
                in_weather_delay = inf.get("WeatherDelay", 0) > 0
                in_late_aircraft = inf.get("LateAircraftDelay", 0) > 0
                in_delayed = (inf.get("ArrDelay", 0) or 0) > DELAY_THRESHOLD_MINUTES
                out_delayed = (outf.get("DepDelay", 0) or 0) > DELAY_THRESHOLD_MINUTES
                cascading = int(in_delayed and out_delayed and (in_weather_delay or in_late_aircraft))

                sequences.append({
                    "date": date_ts,
                    "month": date_ts.month,
                    "year": date_ts.year,
                    "day_of_week": date_ts.dayofweek + 1,
                    "airport_a": airport_a,
                    "airport_b": airport_b,
                    "inbound_arr_time": inf["arr_minutes"],
                    "outbound_dep_time": outf["dep_minutes"],
                    "connection_minutes": gap,
                    "inbound_arr_delay": inf.get("ArrDelay", 0) or 0,
                    "outbound_dep_delay": outf.get("DepDelay", 0) or 0,
                    "inbound_weather_delay": inf.get("WeatherDelay", 0) or 0,
                    "inbound_late_aircraft_delay": inf.get("LateAircraftDelay", 0) or 0,
                    "outbound_weather_delay": outf.get("WeatherDelay", 0) or 0,
                    "cascading_delay": cascading,
                })

    seq_df = pd.DataFrame(sequences)
    seq_df.to_parquet(cache_path, index=False)
    print(f"Built {len(seq_df):,} synthetic sequences, {seq_df['cascading_delay'].sum():,} cascading delays")
    return seq_df


if __name__ == "__main__":
    print("Loading data ...")
    flights = load_flights()
    print(f"Flights: {flights.shape}")

    weather = load_weather()
    print(f"Weather hourly: {weather.shape}")

    print("\nComputing daily weather ...")
    daily = compute_daily_weather(weather)
    print(f"Weather daily: {daily.shape}")

    print("\nMerging flights with weather ...")
    merged = merge_flights_with_daily_weather(flights, daily)
    print(f"Merged: {merged.shape}")

    print("\nBuilding synthetic sequences ...")
    sequences = build_synthetic_sequences(flights)
    print(f"Sequences: {sequences.shape}")
