import math

import pytest

from app.research import describe, rating, risks, thesis


def test_describe_undoes_log_scales():
    assert describe("log_sub_total", math.log1p(63.61)) == "Overall book covered 63.6x"
    assert describe("log_issue_size", math.log(6560)) == "Issue size ₹6,560 cr"
    assert describe("vix", 14.2) == "India VIX at 14.2"
    assert describe("recent_ipo_mean_gain", float("nan")) is None


def test_thesis_splits_and_orders_drivers():
    cols = ["log_sub_qib", "log_sub_total", "vix", "recent_ipo_count", "log_offer_price"]
    vals = [math.log1p(200), math.log1p(70), 15.0, 20.0, math.log(500)]
    impacts = [17.4, 15.0, -0.3, -2.2, 0.8]
    supports, weighs = thesis(cols, vals, impacts)
    assert [p.text for p in supports] == ["QIB book covered 200.0x", "Overall book covered 70.0x", "Offer price ₹500"]
    assert [p.text for p in weighs] == ["20 mainboard listings in the past 90 days"]  # VIX below 0.5 pp is dropped


@pytest.mark.parametrize("expected, low, verdict", [
    (40.0, 5.0, ("SUBSCRIBE", "High")),
    (15.0, -8.0, ("SUBSCRIBE", "Medium")),
    (2.0, -15.0, ("SUBSCRIBE", "Low")),
    (-3.0, -20.0, ("AVOID", "Low")),
    (-10.0, -30.0, ("AVOID", "High")),
])
def test_rating(expected, low, verdict):
    assert rating(expected, low, threshold=-2) == verdict


def test_risks_flags_the_right_things():
    items = risks(expected=5, low=-14, high=40, odds=0.01, sub_total=2.5, nifty_vs_200dma=-1.0, recent_count=15)
    text = " ".join(items)
    assert "below issue price" in text
    assert "Wide outcome range" in text
    assert "1 in 100" in text
    assert "Thin overall demand" in text
    assert "200-day average" in text
    assert "Crowded primary calendar" in text
    assert items[-1].startswith("Model error")


def test_market_risks_dropped_when_model_reads_them_as_positive():
    impacts = {"recent_ipo_count": 1.5, "nifty_vs_200dma": -0.8}
    items = risks(expected=70, low=16, high=116, odds=0.5, sub_total=184, nifty_vs_200dma=-1.8, recent_count=24,
                  impacts=impacts)
    text = " ".join(items)
    assert "Crowded primary calendar" not in text
    assert "200-day average" in text


def test_quiet_case_only_has_model_error():
    items = risks(expected=30, low=10, high=50, odds=0.5, sub_total=40, nifty_vs_200dma=5, recent_count=4)
    assert len(items) == 1
