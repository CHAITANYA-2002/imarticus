import pandas as pd
import pytest

from src.data.market import split_factor_after


def splits(entries):
    return pd.Series({pd.Timestamp(day): ratio for day, ratio in entries}, dtype=float)


def test_no_splits_means_factor_one():
    assert split_factor_after(splits([]), pd.Timestamp("2019-10-14")) == 1.0


def test_only_splits_after_listing_count():
    # IRCTC: listed 2019-10-14, 1:5 split in 2021. A split before listing must be ignored.
    history = splits([("2015-01-01", 2.0), ("2021-10-28", 5.0)])
    assert split_factor_after(history, pd.Timestamp("2019-10-14")) == 5.0


def test_bonus_and_split_compound():
    # Nykaa style: 5:1 bonus recorded by Yahoo as a 6x split, then a later 2x split.
    history = splits([("2022-11-10", 6.0), ("2024-01-01", 2.0)])
    assert split_factor_after(history, pd.Timestamp("2021-11-10")) == 12.0


def test_consolidation_gives_factor_below_one():
    history = splits([("2020-05-01", 0.01)])
    assert split_factor_after(history, pd.Timestamp("2010-01-21")) == pytest.approx(0.01)


def test_split_on_listing_day_is_not_counted():
    history = splits([("2021-11-10", 2.0)])
    assert split_factor_after(history, pd.Timestamp("2021-11-10")) == 1.0
