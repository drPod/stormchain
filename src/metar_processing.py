"""Process raw METAR data into daily aviation weather features."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PROCESSED_DIR


def process_metar() -> pd.DataFrame:
    """Process raw METAR observations into daily aviation weather summaries.

    Key aviation features derived:
    - IFR hours: ceiling < 1000ft AND/OR visibility < 3 SM
    - LIFR hours: ceiling < 500ft AND/OR visibility < 1 SM
    - VFR hours: ceiling >= 3000ft AND visibility >= 5 SM
    - Thunderstorm hours: wxcodes contains 'TS'
    - Fog hours: wxcodes contains 'FG' or 'BR'
    - Low visibility hours: vsby < 3
    - Real ceiling height stats (min, mean, p10)
    - Real visibility stats (min, mean, p10)
    """
    cache_path = PROCESSED_DIR / "metar_daily.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    print("Loading METAR data ...")
    metar = pd.read_parquet(PROCESSED_DIR / "metar_hourly.parquet")
    metar["valid"] = pd.to_datetime(metar["valid"], errors="coerce")
    metar["date"] = metar["valid"].dt.normalize()
    metar["hour"] = metar["valid"].dt.hour

    # Get lowest ceiling from the 4 sky layers
    # skyl1-4 are ceiling heights in feet, skyc1-4 are coverage codes
    # Ceiling = lowest layer with BKN or OVC coverage
    for i in range(1, 5):
        sky_col = f"skyc{i}"
        lvl_col = f"skyl{i}"
        if sky_col in metar.columns:
            metar[sky_col] = metar[sky_col].astype(str).str.strip()
        if lvl_col in metar.columns:
            metar[lvl_col] = pd.to_numeric(metar[lvl_col], errors="coerce")

    # Compute ceiling: lowest BKN or OVC layer
    def get_ceiling(row):
        for i in range(1, 5):
            cov = str(row.get(f"skyc{i}", "")).strip()
            lvl = row.get(f"skyl{i}")
            if cov in ("BKN", "OVC") and pd.notna(lvl):
                return lvl
        return 99999  # Clear sky = unlimited ceiling

    print("Computing ceiling heights ...")
    metar["ceiling_ft"] = metar.apply(get_ceiling, axis=1)

    # Visibility
    metar["vsby"] = pd.to_numeric(metar["vsby"], errors="coerce")

    # Weather codes
    metar["wxcodes"] = metar["wxcodes"].astype(str).fillna("")

    # Flight categories
    metar["is_ifr"] = (metar["ceiling_ft"] < 1000) | (metar["vsby"] < 3)
    metar["is_lifr"] = (metar["ceiling_ft"] < 500) | (metar["vsby"] < 1)
    metar["is_vfr"] = (metar["ceiling_ft"] >= 3000) & (metar["vsby"] >= 5)
    metar["is_mvfr"] = (~metar["is_ifr"]) & (~metar["is_vfr"])  # Marginal VFR

    # Weather phenomena
    metar["has_thunderstorm"] = metar["wxcodes"].str.contains("TS", na=False)
    metar["has_fog"] = metar["wxcodes"].str.contains("FG|BR", na=False, regex=True)
    metar["has_snow"] = metar["wxcodes"].str.contains("SN", na=False)
    metar["has_freezing"] = metar["wxcodes"].str.contains("FZ", na=False)
    metar["has_rain"] = metar["wxcodes"].str.contains("RA|DZ", na=False, regex=True)
    metar["low_vis"] = metar["vsby"] < 3

    # Wind
    metar["gust"] = pd.to_numeric(metar["gust"], errors="coerce")
    metar["sknt"] = pd.to_numeric(metar["sknt"], errors="coerce")
    metar["high_wind"] = metar["gust"] > 30  # knots

    print("Aggregating to daily ...")
    daily = metar.groupby(["station", "date"]).agg(
        # Flight category hours
        metar_ifr_hours=("is_ifr", "sum"),
        metar_lifr_hours=("is_lifr", "sum"),
        metar_vfr_hours=("is_vfr", "sum"),
        metar_mvfr_hours=("is_mvfr", "sum"),
        # Weather phenomena hours
        metar_thunderstorm_hours=("has_thunderstorm", "sum"),
        metar_fog_hours=("has_fog", "sum"),
        metar_snow_hours=("has_snow", "sum"),
        metar_freezing_hours=("has_freezing", "sum"),
        metar_rain_hours=("has_rain", "sum"),
        metar_low_vis_hours=("low_vis", "sum"),
        metar_high_wind_hours=("high_wind", "sum"),
        # Ceiling stats
        metar_ceiling_min=("ceiling_ft", "min"),
        metar_ceiling_mean=("ceiling_ft", "mean"),
        metar_ceiling_p10=("ceiling_ft", lambda x: x.quantile(0.1)),
        # Visibility stats
        metar_vis_min=("vsby", "min"),
        metar_vis_mean=("vsby", "mean"),
        metar_vis_p10=("vsby", lambda x: x.quantile(0.1)),
        # Wind stats
        metar_gust_max=("gust", "max"),
        metar_wind_max=("sknt", "max"),
        # Observation count
        metar_obs_count=("valid", "size"),
    ).reset_index()

    # Rename station to airport for consistency
    daily = daily.rename(columns={"station": "airport"})

    daily.to_parquet(cache_path, index=False)
    print(f"Saved METAR daily features: {len(daily):,} rows, {daily['airport'].nunique()} airports")
    print(f"\nSample IFR stats:")
    ifr_summary = daily.groupby("airport")["metar_ifr_hours"].mean().sort_values(ascending=False)
    print("  Top 10 airports by avg daily IFR hours:")
    for ap, val in ifr_summary.head(10).items():
        print(f"    {ap}: {val:.1f} hours/day")

    return daily


if __name__ == "__main__":
    daily = process_metar()
    print(f"\nShape: {daily.shape}")
    print(f"Columns: {list(daily.columns)}")
