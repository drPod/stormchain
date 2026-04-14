"""Download BTS flight delay data from Kaggle and weather data from Open-Meteo."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    BTS_RAW_DIR, WEATHER_RAW_DIR, PROCESSED_DIR,
    KAGGLE_DATASET_TRAIN, KAGGLE_DATASET_TEST, KAGGLE_API_TOKEN,
    DFW_IATA, BTS_TRAIN_YEARS, BTS_TEST_YEAR,
    OPEN_METEO_BASE_URL, OPEN_METEO_HOURLY_VARS,
    WEATHER_BATCH_SIZE, WEATHER_REQUEST_DELAY,
)


# ---------------------------------------------------------------------------
# BTS Data from Kaggle
# ---------------------------------------------------------------------------

def download_kaggle_dataset(dataset_ref: str, output_dir: Path) -> None:
    """Download and unzip a Kaggle dataset."""
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["KAGGLE_API_TOKEN"] = KAGGLE_API_TOKEN

    venv_kaggle = Path(__file__).parent.parent / ".venv" / "bin" / "kaggle"
    kaggle_cmd = str(venv_kaggle) if venv_kaggle.exists() else "kaggle"

    cmd = [
        kaggle_cmd, "datasets", "download",
        "-d", dataset_ref,
        "-p", str(output_dir),
        "--unzip",
    ]
    print(f"Downloading {dataset_ref} ...")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
        raise RuntimeError(f"Kaggle download failed: {result.stderr}")
    print(f"Downloaded to {output_dir}")


def download_bts_data() -> None:
    """Download both training and test BTS datasets from Kaggle."""
    train_dir = BTS_RAW_DIR / "train"
    test_dir = BTS_RAW_DIR / "test"

    if not any(train_dir.glob("*.csv")):
        download_kaggle_dataset(KAGGLE_DATASET_TRAIN, train_dir)
    else:
        print(f"Training data already exists in {train_dir}")

    if not any(test_dir.glob("*.csv")):
        download_kaggle_dataset(KAGGLE_DATASET_TEST, test_dir)
    else:
        print(f"Test data already exists in {test_dir}")


def load_and_filter_bts() -> pd.DataFrame:
    """Load BTS CSVs, filter to DFW flights, return combined DataFrame."""
    cache_path = PROCESSED_DIR / "flights_dfw.parquet"
    if cache_path.exists():
        print(f"Loading cached DFW flights from {cache_path}")
        return pd.read_parquet(cache_path)

    download_bts_data()

    dfs = []
    for subdir in ["train", "test"]:
        data_dir = BTS_RAW_DIR / subdir
        for csv_file in sorted(data_dir.glob("*.csv")):
            print(f"Reading {csv_file.name} ...")
            try:
                df = pd.read_csv(csv_file, low_memory=False)
            except Exception as e:
                print(f"  Error reading {csv_file.name}: {e}")
                continue

            # Normalize column names — some datasets use different cases
            col_map = {}
            for col in df.columns:
                col_lower = col.lower().strip()
                if col_lower == "fl_date" or col_lower == "flightdate":
                    col_map[col] = "FlightDate"
                elif col_lower == "year":
                    col_map[col] = "Year"
                elif col_lower == "month":
                    col_map[col] = "Month"
                elif col_lower in ("dayofmonth", "day_of_month"):
                    col_map[col] = "DayofMonth"
                elif col_lower in ("dayofweek", "day_of_week"):
                    col_map[col] = "DayOfWeek"
                elif col_lower in ("reporting_airline", "op_unique_carrier", "mkt_unique_carrier", "carrier", "airline", "airline_code"):
                    col_map[col] = "Reporting_Airline"
                elif col_lower == "origin":
                    col_map[col] = "Origin"
                elif col_lower == "dest":
                    col_map[col] = "Dest"
                elif col_lower in ("crsdeptime", "crs_dep_time"):
                    col_map[col] = "CRSDepTime"
                elif col_lower in ("deptime", "dep_time"):
                    col_map[col] = "DepTime"
                elif col_lower in ("depdelay", "dep_delay"):
                    col_map[col] = "DepDelay"
                elif col_lower in ("depdel15", "dep_del15"):
                    col_map[col] = "DepDel15"
                elif col_lower in ("crsarrtime", "crs_arr_time"):
                    col_map[col] = "CRSArrTime"
                elif col_lower in ("arrtime", "arr_time"):
                    col_map[col] = "ArrTime"
                elif col_lower in ("arrdelay", "arr_delay"):
                    col_map[col] = "ArrDelay"
                elif col_lower in ("arrdel15", "arr_del15"):
                    col_map[col] = "ArrDel15"
                elif col_lower == "cancelled":
                    col_map[col] = "Cancelled"
                elif col_lower in ("cancellationcode", "cancellation_code"):
                    col_map[col] = "CancellationCode"
                elif col_lower in ("carrierdelay", "carrier_delay", "delay_due_carrier"):
                    col_map[col] = "CarrierDelay"
                elif col_lower in ("weatherdelay", "weather_delay", "delay_due_weather"):
                    col_map[col] = "WeatherDelay"
                elif col_lower in ("nasdelay", "nas_delay", "delay_due_nas"):
                    col_map[col] = "NASDelay"
                elif col_lower in ("securitydelay", "security_delay", "delay_due_security"):
                    col_map[col] = "SecurityDelay"
                elif col_lower in ("lateaircraftdelay", "late_aircraft_delay", "delay_due_late_aircraft"):
                    col_map[col] = "LateAircraftDelay"
                elif col_lower == "distance":
                    col_map[col] = "Distance"
                elif col_lower in ("airtime", "air_time"):
                    col_map[col] = "AirTime"

            # Avoid mapping multiple source cols to same target
            seen_targets = set()
            deduped_map = {}
            for src, tgt in col_map.items():
                if tgt not in seen_targets:
                    deduped_map[src] = tgt
                    seen_targets.add(tgt)
            df = df.rename(columns=deduped_map)
            df = df.loc[:, ~df.columns.duplicated()]

            # Filter to DFW flights only
            if "Origin" in df.columns and "Dest" in df.columns:
                df = df[(df["Origin"] == DFW_IATA) | (df["Dest"] == DFW_IATA)]
            else:
                print(f"  Skipping {csv_file.name} — no Origin/Dest columns")
                continue

            # Exclude 2020
            if "Year" not in df.columns and "FlightDate" in df.columns:
                df["FlightDate"] = pd.to_datetime(df["FlightDate"], errors="coerce")
                df["Year"] = df["FlightDate"].dt.year
                df["Month"] = df["FlightDate"].dt.month
                df["DayofMonth"] = df["FlightDate"].dt.day
                df["DayOfWeek"] = df["FlightDate"].dt.dayofweek + 1

            if "Year" in df.columns:
                df = df[df["Year"] != 2020]

            # Keep only standardized columns
            standard_cols = [
                "FlightDate", "Year", "Month", "DayofMonth", "DayOfWeek",
                "Reporting_Airline", "Origin", "Dest",
                "CRSDepTime", "DepTime", "DepDelay", "DepDel15",
                "CRSArrTime", "ArrTime", "ArrDelay", "ArrDel15",
                "Cancelled", "CancellationCode",
                "CarrierDelay", "WeatherDelay", "NASDelay",
                "SecurityDelay", "LateAircraftDelay",
                "Distance", "AirTime",
            ]
            keep = [c for c in standard_cols if c in df.columns]
            df = df[keep]

            if len(df) > 0:
                print(f"  Kept {len(df):,} DFW flights")
                dfs.append(df)

    if not dfs:
        raise RuntimeError("No BTS data loaded!")

    combined = pd.concat(dfs, ignore_index=True)

    # Ensure FlightDate is datetime
    if "FlightDate" in combined.columns:
        combined["FlightDate"] = pd.to_datetime(combined["FlightDate"], errors="coerce")

    # Fill NaN delays with 0 (NaN means no delay breakdown available)
    delay_cols = ["WeatherDelay", "CarrierDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay"]
    for col in delay_cols:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce").fillna(0)

    # Ensure numeric types
    numeric_cols = ["DepDelay", "ArrDelay", "DepDel15", "ArrDel15", "Distance", "AirTime",
                    "CRSDepTime", "DepTime", "CRSArrTime", "ArrTime", "Cancelled"]
    for col in numeric_cols:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(cache_path, index=False)
    print(f"\nSaved {len(combined):,} DFW flights to {cache_path}")
    print(f"Years: {sorted(combined['Year'].dropna().unique().astype(int))}")
    print(f"Unique airports: {combined['Origin'].nunique() + combined['Dest'].nunique()}")

    return combined


# ---------------------------------------------------------------------------
# Weather Data from Open-Meteo
# ---------------------------------------------------------------------------

def fetch_weather_for_airport(
    iata: str, lat: float, lon: float,
    start_date: str, end_date: str,
) -> pd.DataFrame | None:
    """Fetch hourly weather for one airport from Open-Meteo."""
    cache_file = WEATHER_RAW_DIR / f"{iata}_{start_date[:4]}.parquet"
    if cache_file.exists():
        return pd.read_parquet(cache_file)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(OPEN_METEO_HOURLY_VARS),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/Chicago",  # DFW timezone as reference
    }

    for attempt in range(5):
        try:
            resp = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=30)
            if resp.status_code == 429:
                wait = 2 ** (attempt + 2)  # 4, 8, 16, 32, 64 seconds
                print(f"  Rate limited, waiting {wait}s ...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            if attempt == 4:
                print(f"  Error fetching weather for {iata}: {e}")
                return None
            time.sleep(2 ** (attempt + 1))
    else:
        print(f"  Failed after 5 retries for {iata}")
        return None

    hourly = data.get("hourly", {})
    if not hourly or "time" not in hourly:
        print(f"  No hourly data for {iata}")
        return None

    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    df["airport"] = iata
    df["latitude"] = lat
    df["longitude"] = lon

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_file, index=False)
    return df


def fetch_all_weather(airports_df: pd.DataFrame) -> pd.DataFrame:
    """Fetch weather for all airports, all years. Returns combined DataFrame."""
    cache_path = PROCESSED_DIR / "weather_hourly.parquet"
    if cache_path.exists():
        print(f"Loading cached weather from {cache_path}")
        return pd.read_parquet(cache_path)

    years = BTS_TRAIN_YEARS + [BTS_TEST_YEAR]
    all_dfs = []
    total = len(airports_df) * len(years)
    done = 0

    for year in years:
        start = f"{year}-01-01"
        end = f"{year}-12-31"

        for _, row in airports_df.iterrows():
            iata = row["iata"]
            lat = row["latitude"]
            lon = row["longitude"]
            done += 1

            print(f"  [{done}/{total}] {iata} {year} ...", end=" ")
            df = fetch_weather_for_airport(iata, lat, lon, start, end)
            if df is not None:
                print(f"{len(df)} rows")
                all_dfs.append(df)
            else:
                print("FAILED")

            time.sleep(WEATHER_REQUEST_DELAY)

    if not all_dfs:
        raise RuntimeError("No weather data fetched!")

    combined = pd.concat(all_dfs, ignore_index=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(cache_path, index=False)
    print(f"\nSaved {len(combined):,} weather records to {cache_path}")
    return combined


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--bts", action="store_true", help="Download BTS data")
    parser.add_argument("--weather", action="store_true", help="Download weather data")
    parser.add_argument("--all", action="store_true", help="Download everything")
    args = parser.parse_args()

    if args.bts or args.all:
        print("=" * 60)
        print("DOWNLOADING BTS FLIGHT DATA")
        print("=" * 60)
        flights = load_and_filter_bts()
        print(f"\nFlight data shape: {flights.shape}")

    if args.weather or args.all:
        print("\n" + "=" * 60)
        print("DOWNLOADING WEATHER DATA")
        print("=" * 60)
        from src.airport_reference import load_airports
        airports = load_airports()
        weather = fetch_all_weather(airports)
        print(f"\nWeather data shape: {weather.shape}")
