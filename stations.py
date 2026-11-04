"""Station lookup from the MTA static GTFS stops.txt.

Run directly to search for a station's stop ID:
    python stations.py "union sq"
"""

import csv
import sys
from pathlib import Path

STOPS_FILE = Path(__file__).parent / "data" / "stops.txt"


def load_stops():
    """Return {stop_id: stop_name} for every stop and platform."""
    with open(STOPS_FILE, newline="", encoding="utf-8") as f:
        return {row["stop_id"]: row["stop_name"] for row in csv.DictReader(f)}


def search(query):
    """Return (stop_id, name) for parent stations whose name contains query."""
    query = query.lower()
    with open(STOPS_FILE, newline="", encoding="utf-8") as f:
        return [
            (row["stop_id"], row["stop_name"])
            for row in csv.DictReader(f)
            if row["location_type"] == "1" and query in row["stop_name"].lower()
        ]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('usage: python stations.py "station name"')
    for stop_id, name in search(sys.argv[1]):
        print(f"{stop_id:6} {name}")
