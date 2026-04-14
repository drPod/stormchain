"""Fetch remaining weather data with longer delays to avoid rate limits."""

import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import WEATHER_RAW_DIR, OPEN_METEO_BASE_URL, OPEN_METEO_HOURLY_VARS

DELAY = 5  # seconds between requests

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

for i, (iata, lat, lon, year) in enumerate(missing):
    print(f"[{i+1}/{len(missing)}] {iata} {year} ...", end=" ", flush=True)

    cache_file = WEATHER_RAW_DIR / f"{iata}_{year}.parquet"
    if cache_file.exists():
        print("cached")
        continue

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

    for attempt in range(5):
        try:
            resp = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=30)
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"429, wait {wait}s ...", end=" ", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            if attempt == 4:
                print(f"FAILED: {e}")
                data = None
                break
            time.sleep(5 * (attempt + 1))
    else:
        print("FAILED after retries")
        continue

    if data and "hourly" in data:
        df = pd.DataFrame(data["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        df["airport"] = iata
        df["latitude"] = lat
        df["longitude"] = lon
        df.to_parquet(cache_file, index=False)
        print(f"{len(df)} rows")
    else:
        print("no data")

    time.sleep(DELAY)

print(f"\nDone. Total files: {len(list(WEATHER_RAW_DIR.glob('*.parquet')))}")
