"""Fetch remaining weather data after waiting for rate limit to expire."""

import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import WEATHER_RAW_DIR, OPEN_METEO_BASE_URL, OPEN_METEO_HOURLY_VARS, PROCESSED_DIR

def get_missing():
    airports = pd.read_csv("data/reference/airports.csv")
    years = [2019, 2021, 2022, 2023, 2024]
    existing = set(f.stem for f in WEATHER_RAW_DIR.glob("*.parquet"))
    missing = []
    for _, row in airports.iterrows():
        for year in years:
            key = f"{row['iata']}_{year}"
            if key not in existing:
                missing.append((row["iata"], row["latitude"], row["longitude"], year))
    return missing

def fetch_one(iata, lat, lon, year):
    cache_file = WEATHER_RAW_DIR / f"{iata}_{year}.parquet"
    if cache_file.exists():
        return True

    params = {
        "latitude": lat, "longitude": lon,
        "start_date": f"{year}-01-01", "end_date": f"{year}-12-31",
        "hourly": ",".join(OPEN_METEO_HOURLY_VARS),
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
        "precipitation_unit": "inch", "timezone": "America/Chicago",
    }
    resp = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=60)
    if resp.status_code == 429:
        return False
    resp.raise_for_status()
    data = resp.json()
    if "hourly" in data:
        df = pd.DataFrame(data["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        df["airport"] = iata
        df["latitude"] = lat
        df["longitude"] = lon
        df.to_parquet(cache_file, index=False)
        return True
    return False

def rebuild_combined():
    """Rebuild combined weather parquet from individual files."""
    files = sorted(WEATHER_RAW_DIR.glob("*.parquet"))
    dfs = [pd.read_parquet(f) for f in files]
    combined = pd.concat(dfs, ignore_index=True)
    combined["time"] = pd.to_datetime(combined["time"])
    combined.to_parquet(PROCESSED_DIR / "weather_hourly.parquet", index=False)
    print(f"Rebuilt combined weather: {len(combined):,} rows, {combined['airport'].nunique()} airports")

if __name__ == "__main__":
    print("Waiting 55 minutes for rate limit to expire ...")
    time.sleep(55 * 60)

    missing = get_missing()
    print(f"\n{len(missing)} airport-year combos to fetch")

    failed = []
    for i, (iata, lat, lon, year) in enumerate(missing):
        print(f"[{i+1}/{len(missing)}] {iata} {year} ...", end=" ", flush=True)
        try:
            ok = fetch_one(iata, lat, lon, year)
            if ok:
                print("OK")
            else:
                print("rate limited - stopping")
                failed = missing[i:]
                break
        except Exception as e:
            print(f"error: {e}")
            failed.append((iata, lat, lon, year))
        time.sleep(3)  # 3 second delay between requests

    total = len(list(WEATHER_RAW_DIR.glob("*.parquet")))
    print(f"\nTotal weather files: {total}/400")
    if failed:
        print(f"Failed/remaining: {len(failed)}")

    rebuild_combined()
