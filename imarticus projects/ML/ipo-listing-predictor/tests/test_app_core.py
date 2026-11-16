"""The app rebuilds features for one IPO from raw inputs; they must match training exactly."""

import numpy as np
import pandas as pd
import pytest

from app.core import build_features, readable_inputs, recent_ipo_stats, similar_ipos
from src.features.build import FEATURES_PATH, load_index
from src.models.dataset import FEATURES

pytestmark = pytest.mark.skipif(not FEATURES_PATH.exists(), reason="run the data pipeline first")


@pytest.fixture(scope="module")
def history():
    return pd.read_csv(FEATURES_PATH, parse_dates=["listing_date"])


@pytest.fixture(scope="module")
def market():
    return load_index("nifty50"), load_index("india_vix")


@pytest.mark.parametrize("position", [50, 300, 500, 620])
def test_features_for_a_past_ipo_match_the_training_table(history, market, position):
    row = history.iloc[position]
    inputs = readable_inputs(row)
    count, mean_gain = recent_ipo_stats(history, row["listing_date"])
    rebuilt = build_features({k: inputs[k] for k in ["listing_date", "sub_qib", "sub_hni", "sub_rii", "sub_total",
                                                     "issue_size_cr", "offer_price"]},
                             *market, count, mean_gain)
    expected = row[FEATURES].astype(float).to_numpy()
    np.testing.assert_allclose(rebuilt.iloc[0].astype(float).to_numpy(), expected, rtol=1e-9, equal_nan=True)


def test_similar_ipos_returns_closest_subscription_profiles(history):
    target = history.iloc[[400]][["log_sub_total", "log_sub_qib", "log_sub_hni", "log_sub_rii"]]
    nearest = similar_ipos(history, target, k=3)
    assert len(nearest) == 3
    assert history.iloc[400]["ipo_name"] in nearest["ipo_name"].tolist()
