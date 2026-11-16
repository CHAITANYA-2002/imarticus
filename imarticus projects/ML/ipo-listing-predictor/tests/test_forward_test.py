import numpy as np
import pandas as pd
import pytest

from src.forward_test import problems, to_pipeline_rows


def row(**overrides):
    base = {"symbol": "ABC", "company_name": "ABC Limited", "listing_date": "2026-07-01", "nse_open": 120.0,
            "is_mainboard_ipo": "yes", "offer_price": 100.0, "issue_size_cr": 500.0, "sub_qib": 50.0,
            "sub_hni": 30.0, "sub_rii": 10.0, "sub_total": 30.0, "source_url": "https://www.nseindia.com/x"}
    return pd.Series({**base, **overrides})


def test_clean_row_has_no_problems():
    assert problems(row()) == []


@pytest.mark.parametrize("overrides, expected", [
    ({"offer_price": ""}, "offer_price missing"),
    ({"sub_total": -1}, "sub_total must be positive"),
    ({"sub_total": 80.0}, "total subscription outside the QIB/HNI/retail range"),
    ({"nse_open": np.nan}, "no listing-day open price"),
    ({"source_url": ""}, "source_url missing"),
])
def test_problems_are_caught(overrides, expected):
    assert expected in problems(row(**overrides))


@pytest.mark.skipif(not __import__("src.features.build", fromlist=["x"]).FEATURES_PATH.exists(),
                    reason="run the data and model pipeline first")
def test_pipeline_runs_end_to_end_on_made_up_rows(tmp_path):
    """Smoke test only: synthetic rows in a temp file, nothing is saved or reported."""
    from src.forward_test import combined_features, load_new_ipos, predict_new

    filled = pd.DataFrame([
        row(symbol="TEST1", company_name="Test One Ltd", listing_date="2026-07-15"),
        row(symbol="TEST2", company_name="Test Two Ltd", listing_date="2026-09-10", sub_total=200.0),
        row(symbol="TEST3", company_name="Not An IPO Ltd", is_mainboard_ipo="no"),
    ])
    path = tmp_path / "new_ipos.csv"
    filled.to_csv(path, index=False)

    new_rows, bad = load_new_ipos(path)
    assert len(new_rows) == 1 and len(bad) == 1  # TEST2's total is outside its category range
    out = predict_new(combined_features(new_rows))
    assert len(out) == 1
    assert out[["random_forest", "low", "high"]].notna().all().all()
    assert (out["low"] <= out["high"]).all()


def test_to_pipeline_rows_computes_gain_and_ids():
    filled = pd.DataFrame([row(), row(symbol="XYZ", company_name="XYZ Ltd", nse_open=90.0)])
    out = to_pipeline_rows(filled)
    assert out["ipo_id"].tolist() == ["NEW0001", "NEW0002"]
    assert out["target_gain_pct"].tolist() == pytest.approx([20.0, -10.0])
    assert (out["exclude_reason"] == "").all()
    assert pd.api.types.is_datetime64_any_dtype(out["listing_date"])
