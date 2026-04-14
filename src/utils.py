"""Shared utility functions."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))


def hhmm_to_minutes(t):
    """Convert HHMM time format to minutes since midnight."""
    t = int(t)
    return (t // 100) * 60 + (t % 100)


def minutes_to_hhmm(m):
    """Convert minutes since midnight to HHMM string."""
    h = int(m // 60) % 24
    mins = int(m % 60)
    return f"{h:02d}:{mins:02d}"


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles between two points."""
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))
