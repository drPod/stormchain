"""Download IEM ASOS/METAR data for all airports, all years."""

import sys
import time
from pathlib import Path
from io import StringIO

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import REFERENCE_DIR

METAR_DIR = Path("data/raw/metar")
METAR_DIR.mkdir(parents=True, exist_ok=True)

IEM_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

airports = pd.read_csv(REFERENCE_DIR / "airports.csv")
years = [2019, 2021, 2022, 2023, 2024]

total = len(airports) * len(years)
done = 0
failed = []

for _, row in airports.iterrows():
    iata = row["iata"]
    for year in years:
        done += 1
        cache = METAR_DIR / f"{iata}_{year}.parquet"
        if cache.exists():
            print(f"[{done}/{total}] {iata} {year} ... cached")
            continue

        print(f"[{done}/{total}] {iata} {year} ...", end=" ", flush=True)

        params = {
            "station": iata,
            "data": "all",
            "year1": year, "month1": 1, "day1": 1,
            "year2": year, "month2": 12, "day2": 31,
            "tz": "America/Chicago",
            "format": "onlycomma",
            "latlon": "no",
            "missing": "M",
            "trace": "T",
            "direct": "no",
            "report_type": 3,
        }

        for attempt in range(3):
            try:
                resp = requests.get(IEM_URL, params=params, timeout=60)
                if resp.status_code != 200:
                    print(f"HTTP {resp.status_code}", end=" ", flush=True)
                    time.sleep(5)
                    continue

                text = resp.text.strip()
                if len(text) < 100 or "station" not in text[:50]:
                    print("empty/invalid", end=" ", flush=True)
                    time.sleep(2)
                    continue

                df = pd.read_csv(StringIO(text), low_memory=False)
                df["valid"] = pd.to_datetime(df["valid"], errors="coerce")

                # Convert numeric columns
                for col in ["tmpf", "dwpf", "relh", "drct", "sknt", "p01i", "alti",
                            "mslp", "vsby", "gust", "skyl1", "skyl2", "skyl3", "skyl4"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                df.to_parquet(cache, index=False)
                print(f"{len(df)} obs")
                break
            except Exception as e:
                print(f"err:{e}", end=" ", flush=True)
                time.sleep(3)
        else:
            print("FAILED")
            failed.append((iata, year))

        time.sleep(1)  # Be polite

print(f"\nDone: {total - len(failed)}/{total} downloaded")
if failed:
    print(f"Failed: {failed}")

# Build combined parquet
print("Building combined METAR parquet ...")
files = sorted(METAR_DIR.glob("*.parquet"))
dfs = [pd.read_parquet(f) for f in files]
combined = pd.concat(dfs, ignore_index=True)
combined.to_parquet(Path("data/processed/metar_hourly.parquet"), index=False)
print(f"Combined: {len(combined):,} observations, {combined['station'].nunique()} airports")
