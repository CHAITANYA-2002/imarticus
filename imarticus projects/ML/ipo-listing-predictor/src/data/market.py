"""Prices from Yahoo Finance: NIFTY/VIX history and each IPO's listing-day bar.

    python -m src.data.market
"""

import pandas as pd
import yfinance as yf

from src.config import MARKET_START_DATE, MARKET_TICKERS, RAW_MARKET_DIR
from src.data.provenance import record

PRICE_COLUMNS = ["open", "high", "low", "close", "volume"]


def fetch_history(ticker, start, end=None):
    try:
        raw = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
    except Exception as e:  # yfinance doesn't have one error type
        raise RuntimeError(f"yahoo download failed for {ticker}: {e}") from e
    if raw.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw.droplevel(1, axis=1)
    df = raw.rename(columns=str.lower)
    df = df[[c for c in PRICE_COLUMNS if c in df.columns]]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.rename_axis("date")


def fetch_splits(ticker):
    try:
        return yf.Ticker(ticker).splits
    except Exception as e:
        raise RuntimeError(f"yahoo split history failed for {ticker}: {e}") from e


def split_factor_after(splits, after):
    """Product of split ratios after a date (Yahoo records bonus issues as splits too)."""
    if splits.empty:
        return 1.0
    dates = pd.to_datetime(splits.index)
    if dates.tz is not None:
        dates = dates.tz_localize(None)
    later = splits.to_numpy()[dates > after]
    return float(later.prod()) if len(later) else 1.0


def first_trading_bar(symbol, listing_date, window_days=10):
    """Listing-day OHLC at the prices that actually traded.

    Yahoo back-adjusts old prices for every later split/bonus even with
    auto_adjust=False (IRCTC's 626 listing shows up as ~125 after its 1:5 split),
    so multiply back by the split factor.
    """
    ticker = f"{symbol}.NS"
    end = listing_date + pd.Timedelta(days=window_days)
    bars = fetch_history(ticker, start=listing_date.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
    if bars.empty:
        return None
    day = bars.index[0]
    factor = split_factor_after(fetch_splits(ticker), day)
    bar = bars.iloc[0]
    prices = {c: bar[c] * factor for c in ["open", "high", "low", "close"] if c in bar}
    volume = {"volume": bar["volume"] / factor} if "volume" in bar else {}
    return {"symbol": symbol, "bar_date": day, **prices, **volume, "split_factor": factor}


def save_index_history(name, ticker):
    history = fetch_history(ticker, start=MARKET_START_DATE)
    if history.empty:
        raise RuntimeError(f"no history for {ticker}")
    path = RAW_MARKET_DIR / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(path)
    record(path, f"Yahoo Finance via yfinance, ticker {ticker}", note="daily OHLCV, unadjusted")
    return path


def main():
    for name, ticker in MARKET_TICKERS.items():
        saved = pd.read_csv(save_index_history(name, ticker), index_col="date", parse_dates=True)
        print(f"{name}: {len(saved)} days, {saved.index.min():%Y-%m-%d} to {saved.index.max():%Y-%m-%d}")


if __name__ == "__main__":
    main()
