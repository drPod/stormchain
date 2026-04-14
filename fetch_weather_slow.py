"""Slowly fetch remaining weather data — one request every 60s to avoid blocks."""

import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import WEATHER_RAW_DIR, OPEN_METEO_BASE_URL, OPEN_METEO_HOURLY_VARS

airports = pd.read_csv("data/reference/airports.csv")
years = [2019, 2021, 2022, 2023, 2024]

existing = set(f.stem for f in WEATHER_RAW_DIR.glob("*.parquet"))
missing = []
for _, row in airports.iterrows():
    for year in years:
        key = f"{row['iata']}_{year}"
        if key not in existing:
            missing.append((row["iata"], row["latitude"], row["longitude"], year))

print(f"Missing: {len(missing)} airport-year combos")
print(f"Estimated time: {len(missing)} minutes")

# Wait for rate limit to clear
print("Waiting 120s for rate limit to reset ...")
time.sleep(120)

for i, (iata, lat, lon, year) in enumerate(missing):
    cache_file = WEATHER_RAW_DIR / f"{iata}_{year}.parquet"
    if cache_file.exists():
        continue

    print(f"[{i+1}/{len(missing)}] {iata} {year} ...", end=" ", flush=True)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": ",".join(OPEN_METEO_HOURLY_VARS),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/Chicago",
    }

    success = False
    for attempt in range(3):
        try:
            resp = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=60)
            if resp.status_code == 429:
                wait = 120 * (attempt + 1)
                print(f"429, waiting {wait}s ...", end=" ", flush=True)
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
                success = True
            break
        except Exception as e:
            print(f"err: {e}", end=" ", flush=True)
            time.sleep(60)

    if not success:
        print("FAILED")

    # Wait between requests
    time.sleep(10)

total = len(list(WEATHER_RAW_DIR.glob("*.parquet")))
print(f"\nDone. Total files: {total}/400")
