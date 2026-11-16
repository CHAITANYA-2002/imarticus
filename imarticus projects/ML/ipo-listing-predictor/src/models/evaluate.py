"""Step 2: walk-forward evaluation, the calibrated range, and the models the app uses.

Every model is refit each quarter on IPOs known by then. The point model is picked on
2019-2023 only; 2024-2026 is reported as the out-of-sample result.

    python -m src.models.evaluate
"""

import json

import joblib
import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR
from src.models.dataset import TARGET, load_features
from src.models.metrics import interval_scores, pinball_loss, regression_scores
from src.models.quantiles import QuantileSet
from src.models.train import BEST_CONFIGS, MODELS_DIR, SEED, TEST_FROM, columns_for, train_model
from src.models.walk_forward import LAG, conformal_widen, walk_forward

EVAL_FROM = 2019
COVERAGE = 0.8
CONFORMAL_WINDOW = 60
WF_PREDICTIONS = PROCESSED_DIR / "wf_predictions.csv"


def period_scores(frame, column):
    rows = []
    for label, sel in [("2019-2023", frame["year"] < TEST_FROM), ("2024-2026", frame["year"] >= TEST_FROM)]:
        rows.append({"period": label, **regression_scores(frame.loc[sel, TARGET], frame.loc[sel, column])})
    return rows


def quantile_walk_forward(df, mask, params, data):
    df = df.sort_values("listing_date")
    rows = df[mask.reindex(df.index)]
    parts = []
    for quarter, chunk in rows.groupby(rows["listing_date"].dt.to_period("Q")):
        train = df[df["listing_date"] < quarter.start_time - LAG]
        parts.append(pd.DataFrame(QuantileSet(params, data).fit(train).predict(chunk),
                                  index=chunk.index, columns=["p10", "p50", "p90"]))
    return pd.concat(parts)


def range_table(frame):
    rows = []
    for label, sel in [("2019-2023", frame["year"] < TEST_FROM), ("2024-2026", frame["year"] >= TEST_FROM)]:
        part = frame[sel]
        y = part[TARGET]
        rows.append({
            "period": label,
            "raw_coverage": interval_scores(y, part["p10"], part["p90"])["coverage"],
            "raw_width": interval_scores(y, part["p10"], part["p90"])["avg_width"],
            "coverage": interval_scores(y, part["low"], part["high"])["coverage"],
            "width": interval_scores(y, part["low"], part["high"])["avg_width"],
            "pinball_p50": pinball_loss(y, part["p50"], 0.5),
        })
    return pd.DataFrame(rows)


def latest_margin(frame):
    """Conformal margin for the next IPO, from the most recent CONFORMAL_WINDOW outcomes."""
    recent = frame.sort_values("listing_date").tail(CONFORMAL_WINDOW)
    scores = np.maximum(recent["p10"] - recent[TARGET], recent[TARGET] - recent["p90"])
    n = len(scores)
    return float(np.quantile(scores, min(1.0, np.ceil((n + 1) * COVERAGE) / n)))


def main():
    best = json.loads(BEST_CONFIGS.read_text())
    df = load_features().sort_values("listing_date").reset_index(drop=True)
    mask = df["year"] >= EVAL_FROM
    out = df.loc[mask, ["ipo_id", "ipo_name", "symbol", "listing_date", "year", "sub_total", TARGET]].copy()

    scores = []
    for name, cfg in best.items():
        print(f"walk-forward: {name}")
        out[name] = walk_forward(df, mask, lambda train, name=name, cfg=cfg: train_model(name, cfg["params"], cfg["data"], train),
                                 columns_for(name, cfg["data"]))
        scores += [{"model": name, **row} for row in period_scores(out, name)]
    scores = pd.DataFrame(scores)

    dev_scores = scores[scores["period"] == "2019-2023"].set_index("model")["mae"]
    point_model = dev_scores.drop(["median", "bucket_median"]).idxmin()
    print(f"point model picked on 2019-2023: {point_model}")

    q_cfg = best["lightgbm"]
    out = out.join(quantile_walk_forward(df, mask, q_cfg["params"], q_cfg["data"]))
    out["low"], out["high"] = conformal_widen(out, out["p10"], out["p90"], coverage=COVERAGE, window=CONFORMAL_WINDOW)
    ranges = range_table(out)

    out.to_csv(WF_PREDICTIONS, index=False)
    scores.to_csv(PROCESSED_DIR / "wf_results.csv", index=False)
    ranges.to_csv(PROCESSED_DIR / "range_results.csv", index=False)

    # what the app loads: same settings, refit on every IPO we have
    point_cfg = best[point_model]
    deploy = {
        "point_name": point_model,
        "point": train_model(point_model, point_cfg["params"], point_cfg["data"], df),
        "point_columns": columns_for(point_model, point_cfg["data"]),
        "quantiles": QuantileSet(q_cfg["params"], q_cfg["data"]).fit(df),
        "conformal_margin": latest_margin(out),
        "coverage": COVERAGE,
        "trained_on": {"ipos": len(df), "first": str(df["listing_date"].min().date()),
                       "last": str(df["listing_date"].max().date())},
        "seed": SEED,
    }
    joblib.dump(deploy, MODELS_DIR / "deploy.pkl")

    pd.set_option("display.width", 200)
    print("\nwalk-forward scores:")
    print(scores.pivot(index="model", columns="period", values=["mae", "median_ae", "spearman"]).round(2).to_string())
    print("\n80% range (LightGBM quantiles + rolling conformal):")
    print(ranges.round(3).to_string(index=False))
    print(f"\nconformal margin for new IPOs: {deploy['conformal_margin']:.2f} pp")


if __name__ == "__main__":
    main()
