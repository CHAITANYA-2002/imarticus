"""Merge researched rows for post-May-2026 IPOs into data/manual/new_ipos.csv.

Each researched row carries its own source links. Two independent checks decide
whether a row is used in the forward test:
- the listing price a source reports must match the NSE open we get from Yahoo
  (within 3%), which also catches a wrong offer price or a wrong company match;
- the subscription figures must agree across two sources, or come from one source
  with no contradiction (rows marked "conflict" or "not_found" are kept but not used).

    python -m src.data.new_ipos_merge <folder with researched CSVs>
"""

import sys
from pathlib import Path

import pandas as pd

from src.data.market import first_trading_bar
from src.data.new_listings import FILLED_PATH, TEMPLATE_PATH

PRICE_TOLERANCE = 0.03
USABLE_AGREEMENT = {"two_sources", "single_source"}


def price_check(reported, nse_open):
    if pd.isna(nse_open):
        return "no_nse_price"
    if pd.isna(reported):
        return "not_reported"
    return "ok" if abs(reported - nse_open) / nse_open <= PRICE_TOLERANCE else "mismatch"


def include_reason(row):
    """'' if the row is usable, else why not."""
    if str(row["is_mainboard_ipo"]).strip().lower() != "yes":
        return "not a mainboard IPO"
    if row["agreement"] not in USABLE_AGREEMENT:
        return f"sources: {row['agreement']}"
    if row["price_check"] == "mismatch":
        return "reported listing price does not match NSE open"
    if row["price_check"] == "no_nse_price":
        return "no NSE listing price"
    return ""


def fetch_open(symbol, listing_date):
    try:
        bar = first_trading_bar(symbol, pd.Timestamp(listing_date))
    except RuntimeError:
        return None
    return round(bar["open"], 2) if bar else None


def merge(research_dir):
    frames = [pd.read_csv(p, dtype={"symbol": str}) for p in sorted(Path(research_dir).glob("*.csv"))]
    rows = pd.concat(frames, ignore_index=True)
    rows = rows[rows["symbol"].notna() & rows["symbol"].str.strip().ne("")]
    template = pd.read_csv(TEMPLATE_PATH)[["symbol", "nse_open"]]
    rows = rows.merge(template, on="symbol", how="left")

    missing = rows["nse_open"].isna() & rows["is_mainboard_ipo"].astype(str).str.lower().eq("yes")
    rows.loc[missing, "nse_open"] = [fetch_open(s, d) for s, d in zip(rows.loc[missing, "symbol"],
                                                                         rows.loc[missing, "listing_date"],
                                                                         strict=True)]
    reported = pd.to_numeric(rows["listing_open_reported"], errors="coerce")
    rows["price_check"] = [price_check(r, o) for r, o in zip(reported, rows["nse_open"], strict=True)]
    rows["exclude_reason"] = rows.apply(include_reason, axis=1)
    rows["include"] = rows["exclude_reason"].eq("").map({True: "yes", False: "no"})
    return rows.sort_values("listing_date").reset_index(drop=True)


def main():
    research_dir = sys.argv[1] if len(sys.argv) > 1 else "data/manual/research"
    rows = merge(research_dir)
    FILLED_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(FILLED_PATH, index=False)
    ipos = rows[rows["is_mainboard_ipo"].astype(str).str.lower().eq("yes")]
    print(f"{len(rows)} rows, {len(ipos)} mainboard IPOs, {int(rows['include'].eq('yes').sum())} usable")
    print(ipos["agreement"].value_counts().to_dict(), ipos["price_check"].value_counts().to_dict())
    excluded = ipos[ipos["include"] == "no"]
    if len(excluded):
        print(excluded[["symbol", "exclude_reason"]].to_string(index=False))


if __name__ == "__main__":
    main()
