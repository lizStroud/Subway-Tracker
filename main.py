"""Subway arrival sign.

    python main.py D19                  # print arrivals and write preview.png
    python main.py D19 --direction N    # uptown/Bronx-bound only
    sudo python main.py D19 --matrix    # on the Pi, drive the LED panel

Find your station's ID with:  python stations.py "14 st"
"""

import argparse
import logging
import time

import display
import mta
from stations import load_stops

FETCH_INTERVAL = 30  # seconds between API calls
REDRAW_INTERVAL = 5  # seconds between redraws, so minutes count down between fetches


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("station", help="station ID, e.g. D19 (or a platform, e.g. D19N)")
    parser.add_argument("--direction", choices=["N", "S"], help="only show one direction")
    parser.add_argument("--matrix", action="store_true", help="drive the LED matrix instead of writing preview.png")
    parser.add_argument("--once", action="store_true", help="fetch and draw once, then exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    station = args.station.upper()
    if args.direction and len(station) == 3:
        station += args.direction
    print(f"Watching {station} {load_stops().get(station, '(unknown stop ID)')}")

    screen = display.MatrixDisplay() if args.matrix else display.PreviewDisplay()
    arrivals, last_fetch = [], 0
    while True:
        if time.time() - last_fetch >= FETCH_INTERVAL:
            arrivals = mta.get_arrivals(station)
            last_fetch = time.time()
            for a in arrivals[:6]:
                print(f"  {a.route:>3} {a.direction}  {a.minutes():>3} min  {a.destination}")
        screen.show(display.render(arrivals))
        if args.once:
            break
        time.sleep(REDRAW_INTERVAL)


if __name__ == "__main__":
    main()
