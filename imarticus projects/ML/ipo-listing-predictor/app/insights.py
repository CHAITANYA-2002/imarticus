"""Decision helpers built on the existing model and data. Nothing here retrains or changes the model.

- loss_probability: chance of listing below issue price, read off the calibrated range
- what_if: how the call moves if one investor group's demand had been different
- input_warnings: inputs outside what the model has seen
- compare_ipos: several issues side by side
- allotment_plan: retail vs small-HNI route across family accounts
- market_heat: how hot the IPO market is now versus history
"""

import math

import numpy as np
import pandas as pd

from src.backtest import allotment_chance
from src.features.build import subscription_features

MIN_PROB = 0.02
# Usual mainboard book split: QIB 50%, NII (HNI) 15%, retail 35%. Overall = share-weighted average.
BOOK_SHARE = {"sub_qib": 0.50, "sub_hni": 0.15, "sub_rii": 0.35}
SHNI_MIN_APPLICATION = 200_000
WHAT_IF_POINTS = 28
HEAT_WINDOW_DAYS = 90
GROUP_NAMES = {"sub_qib": "QIB", "sub_hni": "HNI / NII", "sub_rii": "Retail", "sub_total": "Overall",
               "offer_price": "Offer price", "issue_size_cr": "Issue size"}


# chance of listing below issue -------------------------------------------------------------------

def loss_probability(low, median, high, at=0.0):
    """P(listing gain < at), treating low/median/high as the 10th/50th/90th percentiles and
    interpolating linearly between them (and with the nearest slope beyond them)."""
    lo, md, hi = sorted([float(low), float(median), float(high)])
    left, right = max(md - lo, 1e-6), max(hi - md, 1e-6)
    if at <= lo:
        p = 0.10 - 0.40 * (lo - at) / left
    elif at <= md:
        p = 0.10 + 0.40 * (at - lo) / left
    elif at <= hi:
        p = 0.50 + 0.40 * (at - md) / right
    else:
        p = 0.90 + 0.40 * (at - hi) / right
    return float(min(max(p, MIN_PROB), 1 - MIN_PROB))


def loss_calibration(predictions):
    """How often IPOs listed below issue, grouped by the loss chance the model gave them.
    predictions: low, p50, high, target_gain_pct (e.g. the walk-forward file)."""
    chance = [loss_probability(a, b, c) for a, b, c in
              zip(predictions["low"], predictions["p50"], predictions["high"], strict=True)]
    frame = pd.DataFrame({"chance": chance, "loss": (predictions["target_gain_pct"] < 0).to_numpy()})
    bands = pd.cut(frame["chance"], [0, 0.10, 0.20, 0.35, 0.50, 1.0],
                   labels=["under 10%", "10–20%", "20–35%", "35–50%", "over 50%"])
    table = frame.groupby(bands, observed=True).agg(IPOs=("loss", "size"), predicted=("chance", "mean"),
                                                    actual=("loss", "mean"))
    return pd.DataFrame({"Model said": table.index.astype(str), "IPOs": table["IPOs"].to_numpy(),
                         "Average predicted %": (table["predicted"] * 100).to_numpy(),
                         "Listed below issue": (table["actual"] * 100).to_numpy()})


# predictions for many rows -----------------------------------------------------------------------

def predict_many(deploy, rule, features, sub_rii):
    """Vectorised version of core.predict: one row of results per feature row."""
    expected = deploy["point"].predict(features[deploy["point_columns"]])
    q = deploy["quantiles"].predict(features)
    margin = deploy["conformal_margin"]
    low, median, high = q[:, 0] - margin, q[:, 1], q[:, 2] + margin
    odds = np.array([allotment_chance(v) for v in np.atleast_1d(sub_rii)], dtype=float)
    return pd.DataFrame({
        "expected": expected, "low": low, "median": median, "high": high,
        "loss_chance": [loss_probability(a, b, c) for a, b, c in zip(low, median, high, strict=True)],
        "call": np.where(expected >= rule["model_threshold"], "SUBSCRIBE", "AVOID"),
        "odds": odds, "ev": expected / 100 * rule["lot_value"] * odds,
    })


# what-if ----------------------------------------------------------------------------------------

def what_if_values(current, points=WHAT_IF_POINTS):
    """Subscription multiples from a tenth of the current figure to ten times it, on a log grid."""
    start, stop = max(0.3, current / 10), max(current * 10, 5.0)
    grid = np.geomspace(start, stop, points)
    return np.unique(np.append(grid, float(current)))


def vary_subscription(ipo, field, values):
    """Copies of the IPO with one investor group's subscription changed. The overall figure moves
    by that group's share of the book, so the four numbers stay consistent."""
    share = BOOK_SHARE[field]
    return pd.DataFrame([
        {**ipo, field: float(v), "sub_total": max(0.0, float(ipo["sub_total"]) + share * (float(v) - ipo[field]))}
        for v in values
    ])


def what_if(deploy, rule, ipo, base_features, field):
    """Expected gain and range across a grid of values for one investor group."""
    rows = vary_subscription(ipo, field, what_if_values(float(ipo[field])))
    subs = subscription_features(rows)
    features = base_features.iloc[[0] * len(rows)].reset_index(drop=True).assign(
        **{c: subs[c].to_numpy() for c in subs.columns if c in base_features.columns})
    return pd.concat([rows[[field, "sub_total"]].rename(columns={field: "value"}),
                      predict_many(deploy, rule, features, rows["sub_rii"].to_numpy())], axis=1)


def flip_point(curve, threshold):
    """First value where the expected gain crosses the Subscribe threshold, or None."""
    above = curve["expected"].to_numpy() >= threshold
    for i in range(1, len(curve)):
        if above[i] != above[i - 1]:
            x0, x1 = curve["value"].iloc[i - 1], curve["value"].iloc[i]
            y0, y1 = curve["expected"].iloc[i - 1], curve["expected"].iloc[i]
            return float(x0 + (threshold - y0) * (x1 - x0) / (y1 - y0))
    return None


# input checks -----------------------------------------------------------------------------------

def _times(value, field):
    return f"₹{value:,.0f}" if field == "offer_price" else (f"₹{value:,.0f} cr" if field == "issue_size_cr"
                                                             else f"{value:,.1f}x")


def input_warnings(ipo, history, low_q=0.01, high_q=0.99):
    """Plain warnings for inputs the model has rarely or never seen, and for inconsistent books."""
    warnings = []
    for field in ["sub_qib", "sub_hni", "sub_rii", "sub_total", "offer_price", "issue_size_cr"]:
        past = history[field].dropna()
        value = float(ipo[field])
        lo, hi = past.quantile(low_q), past.quantile(high_q)
        name = GROUP_NAMES[field]
        if value > hi:
            warnings.append(f"{name} {_times(value, field)} is higher than 99% of past IPOs "
                            f"(highest seen {_times(past.max(), field)}). The model has few cases like this.")
        elif value < lo:
            warnings.append(f"{name} {_times(value, field)} is lower than 99% of past IPOs "
                            f"(lowest seen {_times(past.min(), field)}). The model has few cases like this.")
    groups = [float(ipo[c]) for c in ["sub_qib", "sub_hni", "sub_rii"]]
    if not min(groups) * 0.95 <= float(ipo["sub_total"]) <= max(groups) * 1.05:
        warnings.append(f"Overall {ipo['sub_total']:,.1f}x should sit between the QIB, HNI and retail figures "
                        f"({min(groups):,.1f}x to {max(groups):,.1f}x). Check the numbers.")
    return warnings


# compare ---------------------------------------------------------------------------------------

COMPARE_COLUMNS = ["Issuer", "Listing date", "Offer ₹", "Size ₹ cr", "QIB x", "HNI x", "Retail x", "Overall x"]
COMPARE_FIELDS = dict(zip(COMPARE_COLUMNS[1:], ["listing_date", "offer_price", "issue_size_cr", "sub_qib",
                                               "sub_hni", "sub_rii", "sub_total"], strict=True))


def compare_ipos(table, feature_builder, deploy, rule):
    """Score every complete row of an edited table. feature_builder(ipo_dict) -> one-row features.
    Returns (results sorted by expected value per lot, list of skipped-row messages)."""
    rows, feats, skipped = [], [], []
    for i, r in table.reset_index(drop=True).iterrows():
        name = str(r.get("Issuer") or "").strip() or f"Row {i + 1}"
        values = {field: r.get(col) for col, field in COMPARE_FIELDS.items()}
        numbers = [values[f] for f in ["offer_price", "issue_size_cr", "sub_qib", "sub_hni", "sub_rii", "sub_total"]]
        if pd.isna(values["listing_date"]) or any(pd.isna(v) for v in numbers):
            skipped.append(f"{name}: fill in every column")
            continue
        if min(numbers[:2]) <= 0 or min(numbers[2:]) < 0:
            skipped.append(f"{name}: prices and sizes must be positive, subscriptions zero or more")
            continue
        ipo = {**values, "listing_date": pd.Timestamp(values["listing_date"]),
               **{f: float(values[f]) for f in COMPARE_FIELDS.values() if f != "listing_date"}}
        rows.append({"Issuer": name, **ipo})
        feats.append(feature_builder(ipo))
    if not rows:
        return pd.DataFrame(), skipped
    inputs = pd.DataFrame(rows)
    scored = predict_many(deploy, rule, pd.concat(feats, ignore_index=True), inputs["sub_rii"].to_numpy())
    out = pd.concat([inputs, scored], axis=1).sort_values("ev", ascending=False).reset_index(drop=True)
    return out.assign(rank=range(1, len(out) + 1)), skipped


# allotment planner -----------------------------------------------------------------------------

def shni_application(lot_value, minimum=SHNI_MIN_APPLICATION):
    """Smallest whole number of lots that is above ₹2 lakh (the small-HNI floor)."""
    return (math.floor(minimum / lot_value) + 1) * lot_value


def allotment_plan(lot_value, gain_pct, sub_rii, sub_hni, accounts):
    """Retail (one lot) vs small HNI (minimum application) across `accounts` separate PANs.
    Both are lotteries: retail odds ~ 1 / retail subscription, small-HNI odds ~ 1 / HNI subscription."""
    if lot_value <= 0 or accounts < 1 or sub_rii < 0 or sub_hni < 0:
        raise ValueError("Lot value and accounts must be positive; subscriptions zero or more.")
    routes = [("Retail (1 lot)", lot_value, allotment_chance(sub_rii)),
              ("Small HNI (min ₹2 lakh)", shni_application(lot_value), allotment_chance(sub_hni))]
    rows = []
    for route, application, p in routes:
        expected_profit = accounts * p * application * gain_pct / 100
        blocked = accounts * application
        rows.append({
            "Route": route, "Per account ₹": application, "Money blocked ₹": blocked,
            "Chance per account": p * 100, "Chance of at least one": (1 - (1 - p) ** accounts) * 100,
            "Expected allotments": accounts * p, "Profit if allotted ₹": application * gain_pct / 100,
            "Expected profit ₹": expected_profit, "Return on blocked money %": expected_profit / blocked * 100,
        })
    return pd.DataFrame(rows)


# market heat -----------------------------------------------------------------------------------

def _window(history, end, days=HEAT_WINDOW_DAYS):
    dates = pd.to_datetime(history["listing_date"])
    return history[(dates > end - pd.Timedelta(days=days)) & (dates <= end) & history["target_gain_pct"].notna()]


def market_heat(history, as_of, days=HEAT_WINDOW_DAYS):
    """Listings and average day-one gain over the last `days`, ranked against every month since the data starts."""
    now = _window(history, as_of, days)
    start = pd.to_datetime(history["listing_date"]).min() + pd.Timedelta(days=days)
    months = pd.date_range(start, as_of, freq="ME")
    series = pd.DataFrame([{"date": d, "count": len(w), "mean_gain": w["target_gain_pct"].mean() if len(w) else np.nan}
                           for d in months for w in [_window(history, d, days)]])
    mean_gain = float(now["target_gain_pct"].mean()) if len(now) else math.nan
    past = series["mean_gain"].dropna()
    percentile = float((past <= mean_gain).mean() * 100) if len(now) and len(past) else math.nan
    if not len(now):
        label = "Quiet"
    elif percentile >= 80:
        label = "Hot"
    elif percentile >= 60:
        label = "Warm"
    elif percentile >= 20:
        label = "Normal"
    else:
        label = "Cold"
    return {"count": len(now), "mean_gain": mean_gain, "percentile": percentile, "label": label,
            "series": series, "as_of": as_of}
