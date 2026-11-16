import numpy as np
import pandas as pd
import pytest

from src.features.build import (
    PREDICTION_LAG_DAYS,
    market_mood,
    recent_ipo_heat,
    subscription_features,
)


def index_series(start: str, values) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=len(values))
    return pd.DataFrame({"close": values}, index=pd.DatetimeIndex(dates, name="date"))


def test_market_mood_ignores_prices_after_cutoff():
    # Flat at 100 for 300 days, then a jump to 200. An IPO listing two days into the jump
    # must not see it, because its information cutoff is a week before listing.
    values = [100.0] * 300 + [200.0] * 20
    nifty = index_series("2020-01-01", values)
    vix = index_series("2020-01-01", [15.0] * 320)
    jump_day = nifty.index[300]
    ipos = pd.DataFrame({"listing_date": [jump_day + pd.Timedelta(days=2)]})

    mood = market_mood(ipos, nifty, vix)

    assert mood.loc[0, "nifty_ret_1m"] == pytest.approx(0.0)
    assert mood.loc[0, "nifty_vs_200dma"] == pytest.approx(0.0)
    assert mood.loc[0, "vix"] == pytest.approx(15.0)


def test_market_mood_measures_trend():
    values = list(np.linspace(100, 130, 320))
    nifty = index_series("2020-01-01", values)
    vix = index_series("2020-01-01", [20.0] * 320)
    ipos = pd.DataFrame({"listing_date": [nifty.index[-1]]})
    mood = market_mood(ipos, nifty, vix)
    assert mood.loc[0, "nifty_ret_1m"] > 0
    assert mood.loc[0, "nifty_ret_3m"] > mood.loc[0, "nifty_ret_1m"]
    assert mood.loc[0, "nifty_vs_200dma"] > 0


def test_recent_ipo_heat_uses_only_earlier_listings():
    ipos = pd.DataFrame(
        {
            "listing_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-03-05"]),
            "target_gain_pct": [10.0, 30.0, 50.0, 999.0],
        }
    )
    heat = recent_ipo_heat(ipos, window_days=90)
    # IPO on 2024-03-01: cutoff 2024-02-23; sees Jan and Feb listings only.
    assert heat.loc[2, "recent_ipo_count"] == 2
    assert heat.loc[2, "recent_ipo_mean_gain"] == pytest.approx(20.0)
    # The first IPO has no history.
    assert heat.loc[0, "recent_ipo_count"] == 0
    assert np.isnan(heat.loc[0, "recent_ipo_mean_gain"])
    # 2024-03-05 cutoff is 2024-02-27: the 2024-03-01 listing (and itself) are excluded.
    assert heat.loc[3, "recent_ipo_count"] == 2


def test_relative_subscription_compares_with_earlier_ipos_only():
    from src.features.build import relative_subscription

    dates = pd.to_datetime(["2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01", "2023-05-01", "2023-06-01",
                            "2023-06-03"])
    ipos = pd.DataFrame({
        "listing_date": dates,
        "sub_total": [1.0, 3.0, 7.0, 15.0, 31.0, 63.0, 1000.0],
        "sub_qib": [1.0] * 7,
        "sub_hni": [1.0] * 7,
    })
    rel = relative_subscription(ipos, window_days=365, min_history=5)
    # first five have fewer than 5 earlier IPOs before their cutoff
    assert rel["sub_total_vs_recent"].iloc[:5].isna().all()
    # 2023-06-01: cutoff 2023-05-25 -> five earlier IPOs, log1p median = log1p(7) = log(8)
    assert rel.loc[5, "sub_total_vs_recent"] == pytest.approx(np.log1p(63.0) - np.log1p(7.0))
    # the huge IPO two days later can't see the 2023-06-01 one (after its cutoff), same reference set
    assert rel.loc[6, "sub_total_vs_recent"] == pytest.approx(np.log1p(1000.0) - np.log1p(7.0))


def test_subscription_features():
    ipos = pd.DataFrame(
        {"sub_qib": [100.0, 0.5], "sub_hni": [50.0, 0.5], "sub_rii": [10.0, 1.0], "sub_total": [60.0, 0.7],
         "issue_size_cr": [1000.0, 50.0], "offer_price": [500.0, 10.0]}
    )
    feats = subscription_features(ipos)
    assert feats.loc[0, "log_sub_total"] == pytest.approx(np.log1p(60.0))
    assert feats.loc[0, "qib_to_rii"] == pytest.approx(np.log1p(100.0) - np.log1p(10.0))
    assert feats.loc[1, "fully_subscribed"] == 0
    assert feats.loc[0, "fully_subscribed"] == 1
    assert feats.loc[0, "log_issue_size"] == pytest.approx(np.log(1000.0))


def test_lag_is_a_week():
    assert PREDICTION_LAG_DAYS == 7
