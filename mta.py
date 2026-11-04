"""Fetch upcoming train arrivals from the MTA GTFS-realtime feeds.

The feeds are public and no longer need an API key.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import requests
from google.transit import gtfs_realtime_pb2

from stations import load_stops

BASE_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2F"
FEEDS = {
    "1234567S": "gtfs",
    "ACE": "gtfs-ace",
    "BDFM": "gtfs-bdfm",
    "G": "gtfs-g",
    "JZ": "gtfs-jz",
    "L": "gtfs-l",
    "NQRW": "gtfs-nqrw",
    "SIR": "gtfs-si",
}

log = logging.getLogger(__name__)
STOP_NAMES = load_stops()


@dataclass
class Arrival:
    route: str        # GTFS route_id, e.g. "F", "6X", "GS"
    direction: str    # "N" (uptown / Bronx-bound) or "S" (downtown / Brooklyn-bound)
    destination: str  # name of the trip's last stop
    time: int         # unix timestamp

    def minutes(self, now=None):
        return max(0, int((self.time - (now or time.time())) // 60))


def fetch_feed(path):
    response = requests.get(BASE_URL + path, timeout=10)
    response.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return feed


def arrivals_in_feed(feed, station_id, now):
    """Yield arrivals at station_id (e.g. "D19") or one platform (e.g. "D19N")."""
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        trip = entity.trip_update
        updates = trip.stop_time_update
        if not updates:
            continue
        destination = STOP_NAMES.get(updates[-1].stop_id, "")
        for update in updates:
            # Platform IDs are the 3-character station ID plus N or S.
            if not update.stop_id.startswith(station_id):
                continue
            t =update.arrival.time or update.departure.time
            if t >= now - 30:
                yield Arrival(trip.trip.route_id, update.stop_id[-1], destination, t)


def get_arrivals(station_id, feeds=FEEDS.values()):
    """Return upcoming arrivals at a station, soonest first.

    Fetches every feed in parallel, since the routes serving a station change
    with service changes. A feed that fails is logged and skipped.
    """
    now = time.time()
    arrivals = []
    with ThreadPoolExecutor() as pool:
        futures = {path: pool.submit(fetch_feed, path) for path in feeds}
    for path, future in futures.items():
        try:
            arrivals.extend(arrivals_in_feed(future.result(), station_id, now))
        except Exception as e:
            log.warning("feed %s failed: %s", path, e)
    return sorted(arrivals, key=lambda a: a.time)
