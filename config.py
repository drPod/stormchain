"""Project configuration constants."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

KAGGLE_API_TOKEN = os.getenv("KAGGLE_API_TOKEN", "")

# --- Paths ---
PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
BTS_RAW_DIR = RAW_DIR / "bts"
WEATHER_RAW_DIR = RAW_DIR / "weather"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"
OUTPUT_DIR = PROJECT_DIR / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
MODEL_DIR = OUTPUT_DIR / "model"
SIMULATION_DIR = OUTPUT_DIR / "simulation"

# --- BTS Data ---
BTS_TRAIN_YEARS = [2019, 2021, 2022, 2023]
BTS_TEST_YEAR = 2024
BTS_ALL_YEARS = BTS_TRAIN_YEARS + [BTS_TEST_YEAR]
KAGGLE_DATASET_TRAIN = "patrickzel/flight-delay-and-cancellation-dataset-2019-2023"
KAGGLE_DATASET_TEST = "hrishitpatil/flight-data-2024"
DFW_IATA = "DFW"

BTS_COLUMNS_KEEP = [
    "FlightDate", "Year", "Month", "DayofMonth", "DayOfWeek",
    "Reporting_Airline", "Origin", "Dest",
    "CRSDepTime", "DepTime", "DepDelay", "DepDel15",
    "CRSArrTime", "ArrTime", "ArrDelay", "ArrDel15",
    "Cancelled", "CancellationCode",
    "CarrierDelay", "WeatherDelay", "NASDelay",
    "SecurityDelay", "LateAircraftDelay",
    "Distance", "AirTime",
]

# --- Weather Data ---
OPEN_METEO_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "rain",
    "snowfall",
    "snow_depth",
    "weather_code",
    "cloud_cover",
    "cloud_cover_low",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "surface_pressure",
]
WEATHER_BATCH_SIZE = 10  # airports per API call
WEATHER_REQUEST_DELAY = 2.0  # seconds between API calls

# --- Modeling ---
DELAY_THRESHOLD_MINUTES = 15
COST_PER_DELAY_MINUTE = 75  # USD
MIN_TURNAROUND_MINUTES = 60
RANDOM_STATE = 42

# --- Operational Constraints (FAA Part 117) ---
FAA_MAX_DUTY_HOURS = 14
WOCL_START_HOUR = 2  # Window of Circadian Low start (local time)
WOCL_END_HOUR = 6    # WOCL end

# --- Simulation ---
MONTE_CARLO_TRIALS = 1000
TOP_K_VALUES = [50, 100, 200, 500]

# --- WMO Weather Codes for severe conditions ---
WMO_THUNDERSTORM = {95, 96, 99}
WMO_FREEZING_RAIN = {66, 67}
WMO_FOG = {45, 48}
WMO_HEAVY_RAIN = {63, 65}
WMO_HEAVY_SNOW = {73, 75}
WMO_SEVERE = WMO_THUNDERSTORM | WMO_FREEZING_RAIN | WMO_FOG | WMO_HEAVY_RAIN | WMO_HEAVY_SNOW

# --- US Climate Regions ---
CLIMATE_REGIONS = {
    "Northeast": ["BOS", "JFK", "LGA", "EWR", "PHL", "DCA", "IAD", "BWI", "BDL", "PVD", "SYR", "ROC", "BUF", "ALB", "PIT"],
    "Southeast": ["ATL", "CLT", "MIA", "FLL", "MCO", "TPA", "JAX", "RDU", "GSO", "CHS", "SAV", "PBI", "RSW", "SRQ", "MSY", "BNA", "MEM", "SDF"],
    "Midwest": ["ORD", "MDW", "DTW", "MSP", "STL", "MCI", "IND", "CMH", "CLE", "MKE", "CVG", "DSM", "OMA", "ICT"],
    "South_Central": ["DFW", "IAH", "HOU", "AUS", "SAT", "OKC", "TUL", "LIT", "SHV", "ELP"],
    "Mountain": ["DEN", "SLC", "PHX", "ABQ", "TUS", "BOI", "COS", "BIL"],
    "Pacific": ["LAX", "SFO", "SEA", "SAN", "PDX", "SJC", "OAK", "SMF", "ONT", "SNA", "BUR"],
    "Alaska_Hawaii": ["ANC", "HNL", "OGG", "LIH", "KOA"],
}

# Reverse lookup: airport -> region
AIRPORT_TO_REGION = {}
for region, airports in CLIMATE_REGIONS.items():
    for ap in airports:
        AIRPORT_TO_REGION[ap] = region

# Storm corridors
TORNADO_ALLEY = {"OKC", "TUL", "ICT", "OMA", "DSM", "MCI", "DFW", "AUS", "SAT", "LIT", "MEM", "SHV"}
GULF_COAST_HURRICANE = {"MSY", "HOU", "IAH", "TPA", "MIA", "FLL", "MCO", "JAX", "PBI", "RSW", "SRQ", "MOB"}
NORTHEAST_WINTER_STORM = {"BOS", "JFK", "LGA", "EWR", "PHL", "DCA", "IAD", "BWI", "BDL", "PVD", "SYR", "ROC", "BUF", "ALB", "PIT"}
