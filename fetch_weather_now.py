"""Fetch remaining weather data immediately with 3-second pacing."""

import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import WEATHER_RAW_DIR, PROCESSED_DIR, OPEN_METEO_BASE_URL, OPEN_METEO_HOURLY_VARS

airports = pd.read_csv("data/reference/airports.csv")
years = [2019, 2021, 2022, 2023, 2024]

existing = set(f.stem for f in WEATHER_RAW_DIR.glob("*.parquet"))
missing = []
for _, row in airports.iterrows():
    for year in years:
        key = f"{row['iata']}_{year}"
        if key not in existing:
            missing.append((row["iata"], row["latitude"], row["longitude"], year))

print(f"Fetching {len(missing)} remaining airport-year combos ...")

for i, (iata, lat, lon, year) in enumerate(missing):
    cache_file = WEATHER_RAW_DIR / f"{iata}_{year}.parquet"
    if cache_file.exists():
        continue

    print(f"[{i+1}/{len(missing)}] {iata} {year} ...", end=" ", flush=True)

    params = {
        "latitude": lat, "longitude": lon,
        "start_date": f"{year}-01-01", "end_date": f"{year}-12-31",
        "hourly": ",".join(OPEN_METEO_HOURLY_VARS),
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
        "precipitation_unit": "inch", "timezone": "America/Chicago",
    }

    for attempt in range(3):
        try:
            resp = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=60)
            if resp.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"429, wait {wait}s ...", end=" ", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            if "hourly" in data:
                df = pd.DataFrame(data["hourly"])
                df["time"] = pd.to_datetime(df["time"])
                df["airport"] = iata
                df["latitude"] = lat
                df["longitude"] = lon
                df.to_parquet(cache_file, index=False)
                print(f"{len(df)} rows")
            break
        except Exception as e:
            print(f"err: {e}", end=" ", flush=True)
            time.sleep(10)

    time.sleep(3)

# Rebuild combined parquet
total = len(list(WEATHER_RAW_DIR.glob("*.parquet")))
print(f"\nTotal files: {total}/400")

print("Rebuilding combined weather parquet ...")
files = sorted(WEATHER_RAW_DIR.glob("*.parquet"))
dfs = [pd.read_parquet(f) for f in files]
combined = pd.concat(dfs, ignore_index=True)
combined["time"] = pd.to_datetime(combined["time"])
PROCESSED_DIR.mkdir(exist_ok=True)
combined.to_parquet(PROCESSED_DIR / "weather_hourly.parquet", index=False)
print(f"Combined: {len(combined):,} rows, {combined['airport'].nunique()} airports")
