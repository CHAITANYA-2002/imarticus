"""Would following the model have made a retail investor money?

Every strategy decides before listing whether to apply for one minimum lot, and
sells at the listing-day open. Retail allotment in an oversubscribed IPO is a
lottery, so the expected profit of an application is scaled by the chance of
actually getting shares (about 1 / retail subscription).

    python -m src.backtest
"""

import json

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR
from src.models.dataset import load_features
from src.models.evaluate import WF_PREDICTIONS
from src.models.train import MODELS_DIR

DECISION_RULE = MODELS_DIR / "decision_rule.json"

LOT_VALUE = 15_000  # SEBI keeps the minimum retail application around Rs 14-15k
THRESHOLDS = np.arange(-10, 41, 1.0)
SUB_CUTOFFS = np.array([0, 1, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10, 15, 20, 30, 50])
DEV_YEARS = (2019, 2023)
TEST_YEARS = (2024, 2026)


def allotment_chance(sub_rii):
    """Rough odds that a one-lot retail application gets shares."""
    if pd.isna(sub_rii):
        return float("nan")
    return 1.0 if sub_rii <= 1 else 1.0 / sub_rii


def summarize(df, apply, lot_value=LOT_VALUE):
    picked = df[apply]
    gains = picked["target_gain_pct"]
    odds = picked["sub_rii"].map(allotment_chance)
    expected = (gains / 100 * lot_value * odds).sum()
    return {
        "applied": int(len(picked)),
        "hit_rate": float((gains > 0).mean() * 100) if len(picked) else np.nan,
        "avg_gain": float(gains.mean()) if len(picked) else np.nan,
        "worst_gain": float(gains.min()) if len(picked) else np.nan,
        "expected_allotments": float(odds.sum()),
        "expected_profit": float(expected),
        "profit_if_always_allotted": float((gains / 100 * lot_value).sum()),
        "losses_avoided": int(((df["target_gain_pct"] < 0) & ~apply).sum()),
    }


def bootstrap_difference(profit_a, profit_b, n=10_000, seed=0):
    """Paired bootstrap over IPOs of total profit A minus B: (difference, 2.5%, 97.5%, share <= 0)."""
    diff = np.asarray(profit_a, float) - np.asarray(profit_b, float)
    rng = np.random.default_rng(seed)
    sums = np.array([rng.choice(diff, len(diff)).sum() for _ in range(n)])
    return float(diff.sum()), float(np.percentile(sums, 2.5)), float(np.percentile(sums, 97.5)), float((sums <= 0).mean())


def best_threshold(df, column, candidates=THRESHOLDS, lot_value=LOT_VALUE):
    """Threshold on `column` that maximises expected profit (lowest one on ties)."""
    profits = [summarize(df, df[column] >= t, lot_value)["expected_profit"] for t in candidates]
    return candidates[int(np.argmax(profits))]


def load_backtest_frame():
    preds = pd.read_csv(WF_PREDICTIONS, parse_dates=["listing_date"])
    subs = load_features()[["ipo_id", "sub_rii"]]
    return preds.merge(subs, on="ipo_id", how="left")


def strategies(dev, test):
    """Each strategy as (name, rule description, apply-mask function). Thresholds come from dev only."""
    model_t = best_threshold(dev, "random_forest")
    lookup_t = best_threshold(dev, "bucket_median")
    sub_t = best_threshold(dev, "sub_total", candidates=SUB_CUTOFFS)
    chosen = {"model_threshold": float(model_t), "lookup_threshold": float(lookup_t), "subscription_cutoff": float(sub_t)}
    return chosen, [
        ("Apply to every IPO", "always", lambda d: pd.Series(True, index=d.index)),
        ("Rule: subscribed 30x or more", "sub_total >= 30", lambda d: d["sub_total"] >= 30),
        ("Rule: tuned subscription cutoff", f"sub_total >= {sub_t:g}", lambda d: d["sub_total"] >= sub_t),
        ("Lookup: same-bucket median", f"bucket median >= {lookup_t:g}%", lambda d: d["bucket_median"] >= lookup_t),
        ("Model: random forest", f"predicted gain >= {model_t:g}%", lambda d: d["random_forest"] >= model_t),
    ]


def run():
    df = load_backtest_frame()
    dev = df[df["year"].between(*DEV_YEARS)]
    test = df[df["year"].between(*TEST_YEARS)]
    chosen, plans = strategies(dev, test)
    rows = []
    for period, frame in [("2019-2023", dev), ("2024-2026", test)]:
        for name, rule, mask in plans:
            rows.append({"period": period, "strategy": name, "rule": rule, **summarize(frame, mask(frame))})
    return pd.DataFrame(rows), chosen


def main():
    results, thresholds = run()
    results.to_csv(PROCESSED_DIR / "backtest_results.csv", index=False)
    # the app's Apply/Skip verdict uses the model threshold picked here
    DECISION_RULE.write_text(json.dumps({**thresholds, "picked_on": f"{DEV_YEARS[0]}-{DEV_YEARS[1]}",
                                         "lot_value": LOT_VALUE}, indent=2))
    print("thresholds picked on 2019-2023:", thresholds)
    pd.set_option("display.width", 220)
    cols = ["period", "strategy", "applied", "hit_rate", "avg_gain", "worst_gain", "expected_allotments",
            "expected_profit", "profit_if_always_allotted", "losses_avoided"]
    print(results[cols].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
