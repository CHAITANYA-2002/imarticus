"""Everything the app needs that isn't UI: loading, features for a new IPO, predictions."""

import json
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
import shap

from src.backtest import DECISION_RULE, allotment_chance
from src.config import PROCESSED_DIR
from src.data.market import fetch_history
from src.features.build import cutoff_dates, load_index, market_mood, subscription_features
from src.models.dataset import FEATURES, load_features
from src.models.train import MODELS_DIR

RECENT_WINDOW_DAYS = 90
NEIGHBOUR_COLUMNS = ["log_sub_total", "log_sub_qib", "log_sub_hni", "log_sub_rii"]

LABELS = {
    "log_sub_total": "Total subscription", "log_sub_hni": "HNI subscription", "log_sub_qib": "QIB subscription",
    "log_sub_rii": "Retail subscription", "qib_to_rii": "QIB vs retail demand", "log_issue_size": "Issue size",
    "log_offer_price": "Offer price", "nifty_ret_1m": "NIFTY 1-month return", "nifty_ret_3m": "NIFTY 3-month return",
    "nifty_vs_200dma": "NIFTY vs 200-day average", "vix": "India VIX",
    "recent_ipo_mean_gain": "Recent IPOs' average gain", "recent_ipo_count": "IPOs in last 90 days",
}


@dataclass
class Prediction:
    expected: float
    low: float
    high: float
    apply: bool
    threshold: float
    allotment_odds: float
    expected_value: float
    features: pd.DataFrame
    median: float = float("nan")


LIVE_MODEL = MODELS_DIR / "deploy_live.pkl"
LIVE_FEATURES = PROCESSED_DIR / "ipo_features_live.csv"
FORWARD_PREDICTIONS = PROCESSED_DIR / "forward_predictions.csv"


def load_models():
    """Prefer the model refit with the forward-test IPOs (src.forward_test), else the main one."""
    deploy = joblib.load(LIVE_MODEL if LIVE_MODEL.exists() else MODELS_DIR / "deploy.pkl")
    rule = json.loads(DECISION_RULE.read_text())
    return deploy, rule


def load_history():
    return load_features(LIVE_FEATURES) if LIVE_FEATURES.exists() else load_features()


def load_out_of_sample_predictions():
    """Walk-forward predictions (2019 - May 2026) plus forward-test predictions, if any."""
    wf = pd.read_csv(PROCESSED_DIR / "wf_predictions.csv", parse_dates=["listing_date"])
    wf["period"] = wf["year"].map(lambda y: "2019–2023" if y < 2024 else "2024 – May 2026")
    if FORWARD_PREDICTIONS.exists():
        fwd = pd.read_csv(FORWARD_PREDICTIONS, parse_dates=["listing_date"])
        fwd = fwd[[c for c in wf.columns if c in fwd.columns]].assign(
            year=fwd["listing_date"].dt.year, period="Jun – Nov 2026 (forward test)")
        wf = pd.concat([wf, fwd], ignore_index=True)
    return wf


def load_market(live=True):
    """Saved NIFTY/VIX history, topped up from Yahoo when possible. Returns (nifty, vix, note)."""
    nifty, vix = load_index("nifty50"), load_index("india_vix")
    if not live:
        return nifty, vix, f"saved data up to {nifty.index.max():%d %b %Y}"
    try:
        start = (nifty.index.max() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        fresh_nifty, fresh_vix = fetch_history("^NSEI", start), fetch_history("^INDIAVIX", start)
        # Yahoo sometimes returns a row with no close for the current session; drop it
        fresh_nifty, fresh_vix = fresh_nifty.dropna(subset=["close"]), fresh_vix.dropna(subset=["close"])
    except RuntimeError:
        return nifty, vix, f"live fetch failed, using saved data up to {nifty.index.max():%d %b %Y}"
    if fresh_nifty.empty:
        return nifty, vix, f"no new prices, using saved data up to {nifty.index.max():%d %b %Y}"
    nifty = pd.concat([nifty, fresh_nifty]).pipe(lambda d: d[~d.index.duplicated(keep="last")]).sort_index()
    vix = pd.concat([vix, fresh_vix]).pipe(lambda d: d[~d.index.duplicated(keep="last")]).sort_index()
    return nifty, vix, f"live, up to {nifty.index.max():%d %b %Y}"


def recent_ipo_stats(history, listing_date):
    """Count and average gain of IPOs that listed in the 90 days before the info cutoff.

    Same definition as recent_ipo_heat() in the training features.
    """
    cutoff = cutoff_dates(pd.Series([listing_date])).iloc[0]
    window = history[(history["listing_date"] < cutoff)
                     & (history["listing_date"] >= cutoff - pd.Timedelta(days=RECENT_WINDOW_DAYS))]
    mean_gain = float(window["target_gain_pct"].mean()) if len(window) else float("nan")
    return len(window), mean_gain


def build_features(ipo, nifty, vix, recent_count, recent_mean_gain):
    """One-row feature frame for a new IPO, built with the same functions as training.

    ipo: dict with listing_date, sub_qib, sub_hni, sub_rii, sub_total, issue_size_cr, offer_price.
    """
    row = pd.DataFrame([ipo]).assign(listing_date=lambda d: pd.to_datetime(d["listing_date"]))
    features = pd.concat([subscription_features(row), market_mood(row, nifty, vix)], axis=1)
    features = features.assign(recent_ipo_count=recent_count, recent_ipo_mean_gain=recent_mean_gain)
    return features[FEATURES]


def predict(deploy, rule, features, sub_rii):
    expected = float(deploy["point"].predict(features[deploy["point_columns"]])[0])
    p10, p50, p90 = deploy["quantiles"].predict(features)[0]
    margin = deploy["conformal_margin"]
    odds = allotment_chance(sub_rii)
    return Prediction(
        expected=expected,
        low=float(p10 - margin),
        high=float(p90 + margin),
        apply=expected >= rule["model_threshold"],
        threshold=rule["model_threshold"],
        allotment_odds=odds,
        expected_value=expected / 100 * rule["lot_value"] * odds,
        features=features,
        median=float(p50),
    )


def make_explainer(deploy):
    return shap.TreeExplainer(deploy["point"][-1])


def explain(deploy, explainer, features):
    """SHAP contribution of each feature to this prediction, in percentage points."""
    X = features[deploy["point_columns"]]
    imputed = deploy["point"][:-1].transform(X)
    values = explainer.shap_values(imputed)[0]
    shown = [f"{LABELS[c]}" for c in X.columns]
    out = pd.DataFrame({"column": X.columns, "feature": shown, "value": X.iloc[0].to_numpy(), "impact": values})
    return out.reindex(out["impact"].abs().sort_values(ascending=False).index), float(explainer.expected_value)


def similar_ipos(history, features, k=5):
    """Past IPOs with the most similar subscription profile (all four multiples)."""
    cols = NEIGHBOUR_COLUMNS
    scale = history[cols].std()
    distance = (((history[cols] - features[cols].iloc[0]) / scale) ** 2).sum(axis=1) ** 0.5
    nearest = history.loc[distance.nsmallest(k).index]
    return nearest[["ipo_name", "listing_date", "sub_qib", "sub_hni", "sub_rii", "sub_total", "target_gain_pct"]]


def readable_inputs(row):
    """Raw inputs for a past IPO from the feature table (for the 'try a past IPO' picker)."""
    return {
        "name": row["ipo_name"],
        "listing_date": row["listing_date"].date(),
        "offer_price": float(row["offer_price"]),
        "issue_size_cr": float(row["issue_size_cr"]),
        "sub_qib": float(row["sub_qib"]),
        "sub_hni": float(row["sub_hni"]),
        "sub_rii": float(row["sub_rii"]),
        "sub_total": float(row["sub_total"]),
        "actual_gain": float(row["target_gain_pct"]),
    }


def is_valid_subscription(values):
    return all(np.isfinite(v) and v >= 0 for v in values)
