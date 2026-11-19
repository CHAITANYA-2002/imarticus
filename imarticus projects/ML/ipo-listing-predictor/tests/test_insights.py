"""Decision helpers built on the existing model: loss chance, what-if, input checks, allotment, market heat."""

import numpy as np
import pandas as pd
import pytest

from app import insights

IPO = {"listing_date": pd.Timestamp("2026-11-25"), "offer_price": 250.0, "issue_size_cr": 800.0,
       "sub_qib": 40.0, "sub_hni": 25.0, "sub_rii": 8.0, "sub_total": 25.0}


# loss chance -----------------------------------------------------------------------------------

@pytest.mark.parametrize(("low", "median", "high", "expected"), [
    (-10, 10, 30, 0.30),   # zero sits halfway between P10 and P50
    (0, 10, 30, 0.10),     # zero is the P10
    (-30, -10, 10, 0.70),  # zero halfway between P50 and P90
    (-20, 0, 20, 0.50),
])
def test_loss_probability_interpolates_the_range(low, median, high, expected):
    assert insights.loss_probability(low, median, high) == pytest.approx(expected)


def test_loss_probability_tails_are_capped():
    assert insights.loss_probability(50, 80, 120) == pytest.approx(insights.MIN_PROB)
    assert insights.loss_probability(-120, -80, -50) == pytest.approx(1 - insights.MIN_PROB)


def test_loss_probability_survives_a_degenerate_range():
    assert 0 < insights.loss_probability(5, 5, 5) < 1


def test_loss_calibration_groups_by_predicted_band():
    wf = pd.DataFrame({"low": [-30, -30, 10, 10], "p50": [-10, -10, 30, 30], "high": [10, 10, 50, 50],
                       "target_gain_pct": [-5, 3, 20, 25]})
    table = insights.loss_calibration(wf)
    assert table["IPOs"].sum() == 4
    top = table.iloc[-1]
    assert top["Listed below issue"] == pytest.approx(50.0)


# what-if ---------------------------------------------------------------------------------------

def test_vary_subscription_moves_the_total_by_the_book_share():
    rows = insights.vary_subscription(IPO, "sub_qib", [40.0, 140.0])
    assert rows["sub_qib"].tolist() == [40.0, 140.0]
    assert rows.loc[0, "sub_total"] == pytest.approx(25.0)
    assert rows.loc[1, "sub_total"] == pytest.approx(25.0 + 0.5 * 100)
    assert rows["sub_rii"].eq(8.0).all()


def test_vary_subscription_never_goes_negative():
    rows = insights.vary_subscription({**IPO, "sub_total": 1.0}, "sub_qib", [0.0])
    assert rows.loc[0, "sub_total"] >= 0


def test_what_if_values_span_around_the_current_figure():
    values = insights.what_if_values(40.0)
    assert values[0] < 40 < values[-1]
    assert np.all(np.diff(values) > 0)
    assert 40.0 in values


def test_flip_point_finds_where_the_call_changes():
    curve = pd.DataFrame({"value": [1, 2, 4, 8], "expected": [-8.0, -4.0, 0.0, 6.0]})
    assert insights.flip_point(curve, threshold=-2.0) == pytest.approx(3.0)
    assert insights.flip_point(curve.assign(expected=[5.0, 6, 7, 8]), threshold=-2.0) is None


# input warnings --------------------------------------------------------------------------------

@pytest.fixture
def history():
    rng = np.random.default_rng(0)
    n = 300
    return pd.DataFrame({
        "offer_price": rng.uniform(50, 1000, n), "issue_size_cr": rng.uniform(100, 5000, n),
        "sub_qib": rng.uniform(1, 150, n), "sub_hni": rng.uniform(1, 150, n), "sub_rii": rng.uniform(1, 50, n),
        "sub_total": rng.uniform(1, 100, n),
    })


def test_no_warnings_for_ordinary_inputs(history):
    assert insights.input_warnings(IPO, history) == []


def test_warns_when_an_input_is_beyond_past_ipos(history):
    warnings = insights.input_warnings({**IPO, "sub_qib": 900.0, "sub_total": 470.0}, history)
    assert any("QIB" in w and "higher than" in w for w in warnings)


def test_warns_when_total_is_outside_the_categories(history):
    warnings = insights.input_warnings({**IPO, "sub_total": 90.0}, history)
    assert any("Overall" in w for w in warnings)


# allotment planner -----------------------------------------------------------------------------

def test_allotment_plan_retail_and_small_hni():
    plan = insights.allotment_plan(lot_value=15_000, gain_pct=20.0, sub_rii=10.0, sub_hni=40.0, accounts=3)
    retail = plan.set_index("Route").loc["Retail (1 lot)"]
    assert retail["Chance per account"] == pytest.approx(10.0)
    assert retail["Chance of at least one"] == pytest.approx((1 - 0.9 ** 3) * 100)
    assert retail["Money blocked ₹"] == 45_000
    assert retail["Expected profit ₹"] == pytest.approx(3 * 0.1 * 15_000 * 0.2)
    shni = plan.set_index("Route").loc["Small HNI (min ₹2 lakh)"]
    assert shni["Money blocked ₹"] == 3 * 210_000  # 14 lots of 15,000, just above 2 lakh
    assert shni["Chance per account"] == pytest.approx(2.5)


def test_allotment_plan_rejects_bad_inputs():
    with pytest.raises(ValueError):
        insights.allotment_plan(lot_value=0, gain_pct=5, sub_rii=2, sub_hni=2, accounts=1)
    with pytest.raises(ValueError):
        insights.allotment_plan(lot_value=15_000, gain_pct=5, sub_rii=2, sub_hni=2, accounts=0)


# market heat -----------------------------------------------------------------------------------

def test_market_heat_reads_the_last_90_days():
    dates = pd.date_range("2020-01-01", "2026-11-01", freq="10D")
    gains = np.where(dates >= "2026-08-01", 40.0, 5.0)
    hist = pd.DataFrame({"listing_date": dates, "target_gain_pct": gains})
    as_of = pd.Timestamp("2026-11-05")
    heat = insights.market_heat(hist, as_of=as_of)
    assert heat["count"] == ((dates > as_of - pd.Timedelta(days=90)) & (dates <= as_of)).sum() > 0
    assert heat["mean_gain"] == pytest.approx(40.0)
    assert heat["percentile"] > 90
    assert heat["label"] == "Hot"
    assert len(heat["series"]) > 50


def test_market_heat_with_no_recent_listings():
    hist = pd.DataFrame({"listing_date": pd.to_datetime(["2020-01-01", "2020-02-01"]), "target_gain_pct": [5.0, 6.0]})
    heat = insights.market_heat(hist, as_of=pd.Timestamp("2026-11-05"))
    assert heat["count"] == 0
    assert heat["label"] == "Quiet"


# with the real model ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def model():
    from app import core
    from src.models.train import MODELS_DIR
    if not (MODELS_DIR / "deploy.pkl").exists():
        pytest.skip("run the pipeline first")
    deploy, rule = core.load_models()
    history = core.load_history()
    from src.features.build import load_index
    nifty, vix = load_index("nifty50"), load_index("india_vix")

    def build(ipo):
        count, mean_gain = core.recent_ipo_stats(history, ipo["listing_date"])
        return core.build_features(ipo, nifty, vix, count, mean_gain)
    return deploy, rule, build


def test_what_if_current_value_matches_the_single_prediction(model):
    from app import core
    deploy, rule, build = model
    features = build(IPO)
    curve = insights.what_if(deploy, rule, IPO, features, "sub_qib")
    single = core.predict(deploy, rule, features, IPO["sub_rii"])
    at_current = curve[curve["value"] == IPO["sub_qib"]].iloc[0]
    assert at_current["expected"] == pytest.approx(single.expected)
    assert at_current["low"] == pytest.approx(single.low)
    assert curve["low"].le(curve["high"]).all()


def test_compare_ranks_complete_rows_and_skips_incomplete(model):
    deploy, rule, build = model
    table = pd.DataFrame([
        {"Issuer": "Strong", "Listing date": IPO["listing_date"], "Offer ₹": 250.0, "Size ₹ cr": 800.0,
         "QIB x": 150.0, "HNI x": 200.0, "Retail x": 40.0, "Overall x": 120.0},
        {"Issuer": "Weak", "Listing date": IPO["listing_date"], "Offer ₹": 250.0, "Size ₹ cr": 800.0,
         "QIB x": 1.1, "HNI x": 0.5, "Retail x": 0.9, "Overall x": 0.9},
        {"Issuer": "Half", "Listing date": IPO["listing_date"], "Offer ₹": 250.0, "Size ₹ cr": None,
         "QIB x": 1.0, "HNI x": 1.0, "Retail x": 1.0, "Overall x": 1.0},
    ])
    result, skipped = insights.compare_ipos(table, build, deploy, rule)
    assert result["ev"].is_monotonic_decreasing
    assert set(result["Issuer"]) == {"Strong", "Weak"}
    assert result["rank"].tolist() == [1, 2]
    assert skipped == ["Half: fill in every column"]
