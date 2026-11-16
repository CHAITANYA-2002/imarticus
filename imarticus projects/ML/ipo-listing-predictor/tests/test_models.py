import numpy as np
import pandas as pd
import pytest

from src.models.baselines import BucketMedian, MedianBaseline
from src.models.dataset import time_split, year_folds
from src.models.metrics import interval_scores, regression_scores


@pytest.fixture
def ipos():
    years = np.repeat(np.arange(2015, 2027), 10)
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "year": years,
        "sub_total": rng.uniform(0.5, 200, len(years)),
        "target_gain_pct": rng.normal(10, 20, len(years)),
    })


def test_time_split_has_no_overlap(ipos):
    train, valid, test = time_split(ipos, train_until=2022, valid_year=2023)
    assert train["year"].max() == 2022
    assert set(valid["year"]) == {2023}
    assert test["year"].min() == 2024
    assert len(train) + len(valid) + len(test) == len(ipos)


def test_year_folds_expand_and_never_look_ahead(ipos):
    folds = list(year_folds(ipos, first_valid_year=2019, last_valid_year=2023))
    assert len(folds) == 5
    for valid_year, (train_idx, valid_idx) in zip(range(2019, 2024), folds, strict=True):
        assert ipos.loc[train_idx, "year"].max() < valid_year
        assert set(ipos.loc[valid_idx, "year"]) == {valid_year}
    # each fold trains on more data than the one before
    sizes = [len(train_idx) for train_idx, _ in folds]
    assert sizes == sorted(sizes)


def test_year_folds_leave_a_gap_before_the_validation_year():
    df = pd.DataFrame({
        "listing_date": pd.to_datetime(["2022-06-01", "2022-12-28", "2023-01-03", "2023-05-01"]),
        "year": [2022, 2022, 2023, 2023],
    })
    (train_idx, valid_idx), = list(year_folds(df, 2023, 2023))
    assert list(train_idx) == [0]  # Dec 28 listing is inside the 7-day gap
    assert list(valid_idx) == [2, 3]


def test_median_baseline():
    X = pd.DataFrame({"a": [1, 2, 3, 4]})
    model = MedianBaseline().fit(X, pd.Series([0.0, 5.0, 10.0, 100.0]))
    assert model.predict(X).tolist() == [7.5] * 4


def test_bucket_median_learns_per_bucket():
    X = pd.DataFrame({"sub_total": [0.5, 2.0, 2.5, 50.0, 60.0, 150.0]})
    y = pd.Series([-5.0, 0.0, 2.0, 20.0, 30.0, 60.0])
    model = BucketMedian().fit(X, y)
    new = pd.DataFrame({"sub_total": [2.2, 55.0, 500.0, 15.0]})
    preds = model.predict(new)
    assert preds[0] == pytest.approx(1.0)    # 1-3x bucket
    assert preds[1] == pytest.approx(25.0)   # 30-100x bucket
    assert preds[2] == pytest.approx(60.0)   # 100x+ bucket
    assert preds[3] == pytest.approx(y.median())  # 10-30x unseen in training -> overall median


def test_regression_scores():
    scores = regression_scores(np.array([0.0, 10.0, 20.0]), np.array([0.0, 20.0, 20.0]))
    assert scores["mae"] == pytest.approx(10 / 3)
    assert scores["rmse"] == pytest.approx(np.sqrt(100 / 3))
    assert scores["spearman"] == pytest.approx(0.866, abs=1e-3)


def test_interval_scores():
    y = np.array([5.0, 15.0, 30.0, -10.0])
    lo = np.array([0.0, 0.0, 0.0, 0.0])
    hi = np.array([10.0, 20.0, 20.0, 10.0])
    scores = interval_scores(y, lo, hi)
    assert scores["coverage"] == pytest.approx(0.5)
    assert scores["avg_width"] == pytest.approx(15.0)
