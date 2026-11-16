"""Feature table: only things you'd know before the IPO lists.

Subscription closes 3 working days before listing (T+3, since Dec 2023; up to 6 before
that), so market and recent-IPO features look at data up to 7 calendar days before
the listing date.

    python -m src.features.build
"""

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR, RAW_MARKET_DIR
from src.data.audit import VERIFIED_PATH

PREDICTION_LAG_DAYS = 7
FEATURES_PATH = PROCESSED_DIR / "ipo_features.csv"


def cutoff_dates(listing_dates):
    return pd.to_datetime(listing_dates) - pd.Timedelta(days=PREDICTION_LAG_DAYS)


def index_signals(nifty, vix):
    """Daily market signals, each computed from that day's close and earlier."""
    close = nifty["close"]
    signals = pd.DataFrame(
        {
            "nifty_ret_1w": close.pct_change(5) * 100,
            "nifty_ret_1m": close.pct_change(21) * 100,
            "nifty_ret_3m": close.pct_change(63) * 100,
            "nifty_vs_200dma": (close / close.rolling(200, min_periods=150).mean() - 1) * 100,
        }
    )
    return signals.join(vix["close"].rename("vix"), how="left").ffill().rename_axis("date").reset_index()


def market_mood(ipos, nifty, vix):
    """Market signals as of each IPO's information cutoff (last trading day on or before it)."""
    keys = pd.DataFrame({"row": range(len(ipos)), "cutoff": cutoff_dates(ipos["listing_date"]).to_numpy()})
    merged = pd.merge_asof(
        keys.sort_values("cutoff"), index_signals(nifty, vix), left_on="cutoff", right_on="date", direction="backward"
    )
    return merged.sort_values("row").drop(columns=["row", "cutoff", "date"]).reset_index(drop=True)


def recent_ipo_heat(ipos, window_days=90):
    """Count and mean listing gain of IPOs that listed in the window before each IPO's cutoff."""
    dates = pd.to_datetime(ipos["listing_date"]).to_numpy()
    gains = ipos["target_gain_pct"].to_numpy(dtype=float)
    cutoffs = cutoff_dates(ipos["listing_date"]).to_numpy()
    window = np.timedelta64(window_days, "D")
    rows = []
    for cutoff in cutoffs:
        in_window = (dates < cutoff) & (dates >= cutoff - window) & ~np.isnan(gains)
        count = int(in_window.sum())
        rows.append({"recent_ipo_count": count, "recent_ipo_mean_gain": gains[in_window].mean() if count else np.nan})
    return pd.DataFrame(rows)


def relative_subscription(ipos, window_days=365, min_history=5):
    """Subscription compared with IPOs that listed in the previous year.

    Oversubscription numbers have inflated a lot (median 5x before 2020, 28x after 2023),
    so "100x" means less today than it did in 2021. This puts each IPO against the norm
    of its own time: log1p(own) minus the median log1p of recent IPOs.
    """
    dates = pd.to_datetime(ipos["listing_date"]).to_numpy()
    cutoffs = cutoff_dates(ipos["listing_date"]).to_numpy()
    window = np.timedelta64(window_days, "D")
    out = {}
    for col in ["sub_total", "sub_qib", "sub_hni"]:
        logged = np.log1p(ipos[col].to_numpy(dtype=float))
        values = []
        for own, cutoff in zip(logged, cutoffs, strict=True):
            past = logged[(dates < cutoff) & (dates >= cutoff - window) & ~np.isnan(logged)]
            values.append(own - np.median(past) if len(past) >= min_history else np.nan)
        out[f"{col}_vs_recent"] = values
    return pd.DataFrame(out)


def subscription_features(ipos):
    """Subscription multiples on a log scale (they range from 0.5x to 1000x+) plus issue size."""
    log_sub = {f"log_{col}": np.log1p(ipos[col]) for col in ["sub_qib", "sub_hni", "sub_rii", "sub_total"]}
    return pd.DataFrame(
        {
            **log_sub,
            "qib_to_rii": log_sub["log_sub_qib"] - log_sub["log_sub_rii"],
            "fully_subscribed": (ipos["sub_total"] >= 1).astype(int),
            "log_issue_size": np.log(ipos["issue_size_cr"]),
            "log_offer_price": np.log(ipos["offer_price"]),
        }
    ).reset_index(drop=True)


def load_index(name):
    return pd.read_csv(RAW_MARKET_DIR / f"{name}.csv", index_col="date", parse_dates=True)


def build_feature_table(verified, nifty, vix):
    kept = (
        verified[verified["exclude_reason"].fillna("") == ""]
        .sort_values("listing_date", kind="mergesort")
        .reset_index(drop=True)
    )
    ids = kept[["ipo_id", "ipo_name", "symbol", "listing_date", "sub_qib", "sub_hni", "sub_rii", "sub_total",
                "issue_size_cr", "offer_price", "target_gain_pct", "target_source"]]
    return pd.concat(
        [ids.assign(year=kept["listing_date"].dt.year), subscription_features(kept),
         relative_subscription(kept), market_mood(kept, nifty, vix), recent_ipo_heat(kept)],
        axis=1,
    )


def main():
    verified = pd.read_csv(VERIFIED_PATH, parse_dates=["listing_date"])
    table = build_feature_table(verified, load_index("nifty50"), load_index("india_vix"))
    FEATURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(FEATURES_PATH, index=False)
    print(f"{len(table)} rows x {table.shape[1]} columns -> {FEATURES_PATH}")
    print(table.isna().sum()[lambda s: s > 0].to_dict())


if __name__ == "__main__":
    main()
