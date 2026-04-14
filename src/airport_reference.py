"""Airport reference data: IATA codes, coordinates, timezones, regions."""

import csv
from pathlib import Path

import pandas as pd

from config import REFERENCE_DIR, AIRPORT_TO_REGION

# Major US airports with AA service through DFW
# Format: IATA -> (latitude, longitude, timezone_offset_utc, city, state)
AIRPORTS = {
    # South Central / Texas
    "DFW": (32.8998, -97.0403, -6, "Dallas/Fort Worth", "TX"),
    "AUS": (30.1945, -97.6699, -6, "Austin", "TX"),
    "SAT": (29.5337, -98.4698, -6, "San Antonio", "TX"),
    "IAH": (29.9902, -95.3368, -6, "Houston", "TX"),
    "HOU": (29.6454, -95.2789, -6, "Houston Hobby", "TX"),
    "ELP": (31.8072, -106.3776, -7, "El Paso", "TX"),
    "OKC": (35.3931, -97.6007, -6, "Oklahoma City", "OK"),
    "TUL": (36.1984, -95.8881, -6, "Tulsa", "OK"),
    "LIT": (34.7294, -92.2243, -6, "Little Rock", "AR"),
    "SHV": (32.4466, -93.8256, -6, "Shreveport", "LA"),
    # Northeast
    "JFK": (40.6413, -73.7781, -5, "New York JFK", "NY"),
    "LGA": (40.7769, -73.8740, -5, "New York LaGuardia", "NY"),
    "EWR": (40.6895, -74.1745, -5, "Newark", "NJ"),
    "BOS": (42.3656, -71.0096, -5, "Boston", "MA"),
    "PHL": (39.8721, -75.2411, -5, "Philadelphia", "PA"),
    "DCA": (38.8512, -77.0402, -5, "Washington Reagan", "DC"),
    "IAD": (38.9531, -77.4565, -5, "Washington Dulles", "VA"),
    "BWI": (39.1754, -76.6684, -5, "Baltimore", "MD"),
    "PIT": (40.4919, -80.2329, -5, "Pittsburgh", "PA"),
    "BDL": (41.9389, -72.6832, -5, "Hartford", "CT"),
    "PVD": (41.7240, -71.4283, -5, "Providence", "RI"),
    "SYR": (43.1112, -76.1063, -5, "Syracuse", "NY"),
    "ROC": (43.1189, -77.6724, -5, "Rochester", "NY"),
    "BUF": (42.9405, -78.7322, -5, "Buffalo", "NY"),
    "ALB": (42.7483, -73.8017, -5, "Albany", "NY"),
    # Southeast
    "ATL": (33.6407, -84.4277, -5, "Atlanta", "GA"),
    "CLT": (35.2140, -80.9431, -5, "Charlotte", "NC"),
    "MIA": (25.7959, -80.2870, -5, "Miami", "FL"),
    "FLL": (26.0726, -80.1527, -5, "Fort Lauderdale", "FL"),
    "MCO": (28.4312, -81.3081, -5, "Orlando", "FL"),
    "TPA": (27.9756, -82.5333, -5, "Tampa", "FL"),
    "JAX": (30.4941, -81.6879, -5, "Jacksonville", "FL"),
    "RDU": (35.8776, -78.7875, -5, "Raleigh-Durham", "NC"),
    "GSO": (36.0978, -79.9373, -5, "Greensboro", "NC"),
    "CHS": (32.8986, -80.0405, -5, "Charleston", "SC"),
    "SAV": (32.1276, -81.2021, -5, "Savannah", "GA"),
    "PBI": (26.6832, -80.0956, -5, "West Palm Beach", "FL"),
    "RSW": (26.5362, -81.7552, -5, "Fort Myers", "FL"),
    "SRQ": (27.3954, -82.5544, -5, "Sarasota", "FL"),
    "MSY": (29.9934, -90.2580, -6, "New Orleans", "LA"),
    "BNA": (36.1263, -86.6774, -6, "Nashville", "TN"),
    "MEM": (35.0424, -89.9767, -6, "Memphis", "TN"),
    "SDF": (38.1744, -85.7360, -5, "Louisville", "KY"),
    # Midwest
    "ORD": (41.9742, -87.9073, -6, "Chicago O'Hare", "IL"),
    "MDW": (41.7868, -87.7522, -6, "Chicago Midway", "IL"),
    "DTW": (42.2124, -83.3534, -5, "Detroit", "MI"),
    "MSP": (44.8848, -93.2223, -6, "Minneapolis", "MN"),
    "STL": (38.7487, -90.3700, -6, "St. Louis", "MO"),
    "MCI": (39.2976, -94.7139, -6, "Kansas City", "MO"),
    "IND": (39.7173, -86.2944, -5, "Indianapolis", "IN"),
    "CMH": (39.9980, -82.8919, -5, "Columbus", "OH"),
    "CLE": (41.4058, -81.8539, -5, "Cleveland", "OH"),
    "MKE": (42.9472, -87.8966, -6, "Milwaukee", "WI"),
    "CVG": (39.0488, -84.6678, -5, "Cincinnati", "KY"),
    "DSM": (41.5340, -93.6631, -6, "Des Moines", "IA"),
    "OMA": (41.3032, -95.8941, -6, "Omaha", "NE"),
    "ICT": (37.6499, -97.4331, -6, "Wichita", "KS"),
    # Mountain / West
    "DEN": (39.8561, -104.6737, -7, "Denver", "CO"),
    "SLC": (40.7884, -111.9778, -7, "Salt Lake City", "UT"),
    "PHX": (33.4373, -112.0078, -7, "Phoenix", "AZ"),
    "ABQ": (35.0402, -106.6090, -7, "Albuquerque", "NM"),
    "TUS": (32.1161, -110.9410, -7, "Tucson", "AZ"),
    "BOI": (43.5644, -116.2228, -7, "Boise", "ID"),
    "COS": (38.8058, -104.7009, -7, "Colorado Springs", "CO"),
    # Pacific
    "LAX": (33.9425, -118.4081, -8, "Los Angeles", "CA"),
    "SFO": (37.6213, -122.3790, -8, "San Francisco", "CA"),
    "SEA": (47.4502, -122.3088, -8, "Seattle", "WA"),
    "SAN": (32.7338, -117.1933, -8, "San Diego", "CA"),
    "PDX": (45.5898, -122.5951, -8, "Portland", "OR"),
    "SJC": (37.3626, -121.9290, -8, "San Jose", "CA"),
    "OAK": (37.7213, -122.2208, -8, "Oakland", "CA"),
    "SMF": (38.6953, -121.5908, -8, "Sacramento", "CA"),
    "ONT": (34.0560, -117.6012, -8, "Ontario", "CA"),
    "SNA": (33.6757, -117.8683, -8, "Orange County", "CA"),
    "BUR": (34.2005, -118.3586, -8, "Burbank", "CA"),
    # Alaska / Hawaii
    "ANC": (61.1743, -149.9962, -9, "Anchorage", "AK"),
    "HNL": (21.3245, -157.9251, -10, "Honolulu", "HI"),
    "OGG": (20.8986, -156.4305, -10, "Maui", "HI"),
    "LIH": (21.9760, -159.3390, -10, "Lihue", "HI"),
    "KOA": (19.7388, -156.0456, -10, "Kona", "HI"),
}


def build_airports_csv(output_path: Path | None = None) -> pd.DataFrame:
    """Build airports reference DataFrame and save to CSV."""
    if output_path is None:
        output_path = REFERENCE_DIR / "airports.csv"

    rows = []
    for iata, (lat, lon, tz, city, state) in AIRPORTS.items():
        rows.append({
            "iata": iata,
            "latitude": lat,
            "longitude": lon,
            "tz_offset": tz,
            "city": city,
            "state": state,
            "region": AIRPORT_TO_REGION.get(iata, "Other"),
        })

    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} airports to {output_path}")
    return df


def load_airports() -> pd.DataFrame:
    """Load airports reference data."""
    path = REFERENCE_DIR / "airports.csv"
    if not path.exists():
        return build_airports_csv(path)
    return pd.read_csv(path)


def get_airport_coords(iata: str) -> tuple[float, float] | None:
    """Get (lat, lon) for an airport IATA code."""
    if iata in AIRPORTS:
        return AIRPORTS[iata][0], AIRPORTS[iata][1]
    return None


if __name__ == "__main__":
    df = build_airports_csv()
    print(df.head(10))
    print(f"\nRegion distribution:\n{df['region'].value_counts()}")
