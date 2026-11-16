import pandas as pd

from src.features.build import FEATURES_PATH

TARGET = "target_gain_pct"

SUBSCRIPTION = ["log_sub_qib", "log_sub_hni", "log_sub_rii", "log_sub_total", "qib_to_rii"]
ISSUE = ["log_issue_size", "log_offer_price"]
MARKET = ["nifty_ret_1m", "nifty_ret_3m", "nifty_vs_200dma", "vix", "recent_ipo_mean_gain", "recent_ipo_count"]
RELATIVE = ["sub_total_vs_recent", "sub_qib_vs_recent", "sub_hni_vs_recent"]
FEATURES = SUBSCRIPTION + ISSUE + MARKET

FEATURE_SETS = {
    "base": FEATURES,
    "with_relative": FEATURES + RELATIVE,
}


def load_features(path=FEATURES_PATH):
    return pd.read_csv(path, parse_dates=["listing_date"])


def time_split(df, train_until=2022, valid_year=2023):
    train = df[df["year"] <= train_until]
    valid = df[df["year"] == valid_year]
    test = df[df["year"] > valid_year]
    return train, valid, test


def year_folds(df, first_valid_year=2019, last_valid_year=2023, lag_days=7):
    """Expanding window: train on IPOs that listed before the validation year.

    The last `lag_days` of the previous year are left out too, so an IPO listing on
    Jan 3 is never scored by a model that saw an IPO listing on Dec 30.
    """
    for year in range(first_valid_year, last_valid_year + 1):
        if "listing_date" in df:
            cutoff = pd.Timestamp(year, 1, 1) - pd.Timedelta(days=lag_days)
            train_idx = df.index[df["listing_date"] < cutoff]
        else:
            train_idx = df.index[df["year"] < year]
        valid_idx = df.index[df["year"] == year]
        if len(valid_idx):
            yield train_idx, valid_idx
