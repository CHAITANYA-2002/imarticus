"""Match Kaggle IPOs to NSE symbols, then pull each one's listing-day bar.

Bars are cached in data/interim/listing_bars.csv; a rerun only fetches what's missing.
    python -m src.data.listing_prices
"""

import time

import pandas as pd

from src.config import INTERIM_DIR
from src.data import nse
from src.data.market import first_trading_bar
from src.data.matching import match_ipos

KAGGLE_INTERIM = INTERIM_DIR / "ipos_kaggle.csv"
MATCHED_PATH = INTERIM_DIR / "ipos_matched.csv"
BARS_PATH = INTERIM_DIR / "listing_bars.csv"
PAUSE_SECONDS = 0.4  # don't hammer Yahoo
BAR_COLUMNS = ["symbol", "bar_date", "open", "high", "low", "close", "volume", "split_factor"]


def build_matches():
    ipos = pd.read_csv(KAGGLE_INTERIM, parse_dates=["listing_date"])
    matched = match_ipos(ipos, nse.load_all())
    matched.to_csv(MATCHED_PATH, index=False)
    return matched


def load_cached_bars(path=BARS_PATH):
    empty = pd.DataFrame(columns=[*BAR_COLUMNS, "status"])
    if not path.exists():
        return empty
    cached = pd.read_csv(path, parse_dates=["bar_date"])
    if "split_factor" not in cached.columns:  # cache from before split restoration: refetch
        return empty
    return cached[cached["split_factor"].notna() | (cached["status"] != "ok")]


def fetch_missing_bars(matched, cached):
    todo = matched.dropna(subset=["symbol"])
    todo = todo[~todo["symbol"].isin(cached["symbol"])].drop_duplicates("symbol")
    rows = []
    for n, row in enumerate(todo.itertuples(index=False), start=1):
        try:
            bar = first_trading_bar(row.symbol, pd.Timestamp(row.nse_listing_date))
            rows.append({**bar, "status": "ok"} if bar else {"symbol": row.symbol, "status": "no_data"})
        except RuntimeError as e:
            rows.append({"symbol": row.symbol, "status": f"error: {e}"[:200]})
        if n % 50 == 0:
            print(f"  {n}/{len(todo)}")
        time.sleep(PAUSE_SECONDS)
    frames = [f for f in (cached, pd.DataFrame(rows)) if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else cached


def main():
    matched = build_matches()
    print("matching:", matched["match_method"].value_counts().to_dict())
    bars = fetch_missing_bars(matched, load_cached_bars())
    bars.to_csv(BARS_PATH, index=False)
    print("listing bars:", bars["status"].value_counts().to_dict())


if __name__ == "__main__":
    main()
