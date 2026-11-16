"""Rebuild everything from scratch, in order.

    python -m src.pipeline            # data, features, models, backtest
    python -m src.pipeline --no-download   # reuse data/raw, rebuild the rest
"""

import argparse
import time

from src import backtest
from src.data import audit, kaggle_ipo, listing_prices, market, nse
from src.features import build
from src.models import evaluate, train

DOWNLOAD = [("NSE lists", nse.main), ("Kaggle IPO data", kaggle_ipo.main), ("NIFTY and VIX", market.main),
            ("Listing-day prices", listing_prices.main)]
BUILD = [("Cross-check", audit.main), ("Features", build.main), ("Tuning", train.main),
         ("Walk-forward evaluation", evaluate.main), ("Backtest", backtest.main)]


def run(steps):
    for name, step in steps:
        start = time.time()
        print(f"\n=== {name} ===")
        step()
        print(f"--- {name} done in {time.time() - start:.0f}s")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-download", action="store_true", help="skip downloads and reuse data/raw")
    args = parser.parse_args()
    if not args.no_download:
        run(DOWNLOAD)
    else:
        listing_prices.build_matches()  # matching is cheap and doesn't need the network
    run(BUILD)


if __name__ == "__main__":
    main()
