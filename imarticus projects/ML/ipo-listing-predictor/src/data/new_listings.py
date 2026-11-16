"""Template for IPOs that listed after the Kaggle file ends (14 May 2026).

Pre-fills what official sources give us (NSE's listed-company file for symbol, name and
listing date; Yahoo for the listing-day open) and leaves the rest to be filled by hand from
each IPO's NSE/BSE bid details page, with the source link recorded per row.

    python -m src.data.new_listings
"""

import time

import pandas as pd

from src.config import DATA_DIR
from src.data import nse
from src.data.market import first_trading_bar

KAGGLE_END = pd.Timestamp("2026-05-14")
MANUAL_DIR = DATA_DIR / "manual"
TEMPLATE_PATH = MANUAL_DIR / "new_ipos_template.csv"
FILLED_PATH = MANUAL_DIR / "new_ipos.csv"

# On 17 Aug 2026 ~150 long-established BSE companies were added to NSE's list in one batch.
# None of them were IPOs, so they are left out of the template.
BULK_LISTING_DAYS = [pd.Timestamp("2026-08-17")]

TO_FILL = ["is_mainboard_ipo", "offer_price", "issue_size_cr", "sub_qib", "sub_hni", "sub_rii", "sub_total",
           "source_url"]


def candidates(listed):
    new = listed[(listed["listing_date"] > KAGGLE_END) & (listed["segment"] == "mainboard")]
    new = new[~new["listing_date"].isin(BULK_LISTING_DAYS)]
    return new.sort_values("listing_date")[["symbol", "company_name", "listing_date", "series"]]


def add_listing_open(rows, pause=0.4):
    opens, dates = [], []
    for row in rows.itertuples(index=False):
        try:
            bar = first_trading_bar(row.symbol, row.listing_date)
        except RuntimeError:
            bar = None
        opens.append(round(bar["open"], 2) if bar else None)
        dates.append(bar["bar_date"].date() if bar else None)
        time.sleep(pause)
    return rows.assign(nse_open=opens, first_bar_date=dates)


def main():
    rows = add_listing_open(candidates(nse.load_all()))
    template = rows.assign(**{c: "" for c in TO_FILL})
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    template.to_csv(TEMPLATE_PATH, index=False)
    print(f"{len(template)} candidate listings -> {TEMPLATE_PATH}")
    print(f"listing open found for {template['nse_open'].notna().sum()}")
    if not FILLED_PATH.exists():
        print(f"copy it to {FILLED_PATH.name}, mark is_mainboard_ipo yes/no and fill the blanks")


if __name__ == "__main__":
    main()
