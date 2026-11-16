import numpy as np
import pandas as pd
import pytest

from src.backtest import allotment_chance, best_threshold, summarize


def test_allotment_chance():
    assert allotment_chance(0.8) == 1.0      # undersubscribed: everyone gets shares
    assert allotment_chance(1.0) == 1.0
    assert allotment_chance(4.0) == pytest.approx(0.25)
    assert allotment_chance(100.0) == pytest.approx(0.01)
    assert np.isnan(allotment_chance(float("nan")))


def picks_frame():
    return pd.DataFrame({
        "target_gain_pct": [50.0, -10.0, 5.0, 20.0],
        "sub_rii": [10.0, 1.0, 2.0, 1.0],
        "score": [40.0, -5.0, 2.0, 15.0],
    })


def test_summarize_counts_and_expected_profit():
    df = picks_frame()
    s = summarize(df, apply=df["score"] > 0, lot_value=10_000)
    assert s["applied"] == 3
    assert s["hit_rate"] == pytest.approx(100.0)
    assert s["avg_gain"] == pytest.approx(25.0)
    # 50% * 10k * 0.1 + 5% * 10k * 0.5 + 20% * 10k * 1
    assert s["expected_profit"] == pytest.approx(500 + 250 + 2000)
    assert s["losses_avoided"] == 1


def test_summarize_with_nothing_applied():
    df = picks_frame()
    s = summarize(df, apply=pd.Series(False, index=df.index), lot_value=10_000)
    assert s["applied"] == 0
    assert s["expected_profit"] == 0
    assert np.isnan(s["avg_gain"])


def test_best_threshold_maximises_expected_profit():
    df = picks_frame()
    # skipping only the -10% IPO is best; any threshold between -5 and 2 does that,
    # the lowest such candidate is returned
    assert best_threshold(df, "score", candidates=[-20, -5, 0, 10, 30], lot_value=10_000) == 0
