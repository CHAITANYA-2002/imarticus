import numpy as np
import pandas as pd
import pytest

from src.models.baselines import MedianBaseline
from src.models.walk_forward import bias_correct, walk_forward


def make_ipos():
    dates = pd.date_range("2022-01-10", periods=24, freq="15D")
    return pd.DataFrame({
        "listing_date": dates,
        "year": dates.year,
        "x": np.arange(24.0),
        "target_gain_pct": np.arange(24.0),
    })


def test_walk_forward_trains_only_on_ipos_listed_before_the_cutoff():
    df = make_ipos()
    eval_mask = df["listing_date"] >= "2022-07-01"
    preds = walk_forward(df, eval_mask, lambda train: MedianBaseline().fit(train[["x"]], train["target_gain_pct"]), ["x"])

    assert preds.index.equals(df.index[eval_mask])
    for idx, pred in preds.items():
        quarter_start = df.loc[idx, "listing_date"].to_period("Q").start_time
        allowed = df[df["listing_date"] < quarter_start - pd.Timedelta(days=7)]["target_gain_pct"]
        assert pred == pytest.approx(allowed.median())


def test_bias_correct_uses_only_earlier_listed_errors():
    dates = pd.date_range("2024-01-01", periods=8, freq="30D")
    frame = pd.DataFrame({"listing_date": dates, "target_gain_pct": [10.0] * 8})
    raw = pd.Series([20.0] * 8)  # model always 10 points too high
    corrected = bias_correct(frame, raw, window=3, min_history=2)
    # first two IPOs have fewer than 2 earlier listings -> unchanged
    assert corrected.iloc[0] == 20.0
    assert corrected.iloc[1] == 20.0
    # afterwards the known +10 bias is removed
    assert corrected.iloc[5] == pytest.approx(10.0)


def test_conformal_widens_a_too_narrow_range():
    from src.models.walk_forward import conformal_widen

    dates = pd.date_range("2024-01-01", periods=40, freq="20D")
    y = pd.Series(np.tile([0.0, 30.0], 20))
    frame = pd.DataFrame({"listing_date": dates, "target_gain_pct": y})
    lo, hi = pd.Series([10.0] * 40), pd.Series([20.0] * 40)  # every actual misses by 10
    new_lo, new_hi = conformal_widen(frame, lo, hi, coverage=0.8, window=20, min_history=10)
    assert new_lo.iloc[0] == 10.0 and new_hi.iloc[0] == 20.0   # no history yet
    assert new_lo.iloc[-1] == pytest.approx(0.0)
    assert new_hi.iloc[-1] == pytest.approx(30.0)


def test_bias_correct_ignores_ipos_listing_inside_the_lag():
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-05"])
    frame = pd.DataFrame({"listing_date": dates, "target_gain_pct": [0.0, 0.0, 0.0, 0.0]})
    raw = pd.Series([5.0, 5.0, 5.0, 5.0])
    corrected = bias_correct(frame, raw, window=3, min_history=1)
    # all earlier IPOs listed within 7 days of the last one: not known at its cutoff
    assert corrected.iloc[3] == 5.0
