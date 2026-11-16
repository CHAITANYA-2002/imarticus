import pandas as pd

from src.data.audit import AGREE_TOLERANCE_PP, cross_check, verdict


def test_verdict_buckets():
    assert verdict(51.3, 51.3, "ok") == "agree"
    assert verdict(10.0, 10.0 + AGREE_TOLERANCE_PP - 0.01, "ok") == "agree"
    assert verdict(41.0, 33.3, "ok") == "close"  # BSE vs NSE opening price
    assert verdict(10.0, 25.0, "ok") == "disagree"
    assert verdict(10.0, float("nan"), "no_data") == "no_price"
    assert verdict(float("nan"), 10.0, "ok") == "no_kaggle_gain"
    assert verdict(10.0, float("nan"), None) == "not_on_nse"
    assert verdict(10.0, 10.0, "ok", on_listing_day=False) == "bar_not_listing_day"


def test_target_prefers_nse_price_when_verified():
    from src.data.audit import choose_target

    assert choose_target(41.0, 33.3, "close") == (33.3, "nse_open_yahoo")
    assert choose_target(41.0, 41.5, "agree") == (41.5, "nse_open_yahoo")
    assert choose_target(10.0, 300.0, "disagree") == (10.0, "kaggle_unverified")
    assert choose_target(12.0, float("nan"), "not_on_nse") == (12.0, "kaggle_unverified")


def test_cross_check_recomputes_gain_from_open():
    matched = pd.DataFrame(
        {
            "ipo_id": ["IPO0001", "IPO0002", "IPO0003"],
            "symbol": ["ZOMATO", "BADCO", None],
            "offer_price": [76.0, 100.0, 50.0],
            "list_price": [115.0, 110.0, 55.0],
            "listing_gain_pct": [51.32, 10.0, 10.0],
            "nse_listing_date": pd.to_datetime(["2021-07-23", "2022-01-03", None]),
        }
    )
    bars = pd.DataFrame(
        {
            "symbol": ["ZOMATO", "BADCO"],
            "bar_date": pd.to_datetime(["2021-07-23", "2022-01-10"]),
            "open": [116.0, 140.0],
            "close": [125.85, 141.0],
            "status": ["ok", "ok"],
        }
    )
    checked = cross_check(matched, bars).set_index("ipo_id")

    assert checked.loc["IPO0001", "check"] == "agree"
    assert round(checked.loc["IPO0001", "yf_open_gain_pct"], 2) == 52.63
    assert round(checked.loc["IPO0001", "yf_close_gain_pct"], 2) == 65.59
    assert bool(checked.loc["IPO0001", "bar_on_listing_date"])

    assert checked.loc["IPO0001", "target_source"] == "nse_open_yahoo"

    # BADCO's first Yahoo bar is a week after listing: that price must not be trusted.
    assert not bool(checked.loc["IPO0002", "bar_on_listing_date"])
    assert checked.loc["IPO0002", "check"] == "bar_not_listing_day"
    assert checked.loc["IPO0002", "target_source"] == "kaggle_unverified"
    assert checked.loc["IPO0002", "target_gain_pct"] == 10.0

    assert checked.loc["IPO0003", "check"] == "not_on_nse"
    assert len(checked) == 3
