"""Forward test on IPOs that listed after the training data ends.

Nothing is re-tuned here: the model settings (models/best_configs.json), the Apply
threshold and the 80% range method are the ones fixed on 2010-2023. New IPOs are
predicted walk-forward and scored once. The main pipeline's outputs are not touched.

    python -m src.forward_test
"""

import json

import joblib
import numpy as np
import pandas as pd

from src.backtest import DECISION_RULE, allotment_chance, bootstrap_difference, summarize
from src.config import PROCESSED_DIR, REPORTS_DIR
from src.data.audit import VERIFIED_PATH, markdown_table
from src.data.new_listings import FILLED_PATH
from src.features.build import FEATURES_PATH, build_feature_table, load_index
from src.models.dataset import TARGET
from src.models.evaluate import CONFORMAL_WINDOW, COVERAGE, WF_PREDICTIONS, latest_margin
from src.models.metrics import interval_scores, regression_scores
from src.models.quantiles import QuantileSet
from src.models.train import BEST_CONFIGS, MODELS_DIR, columns_for, train_model
from src.models.walk_forward import LAG, conformal_widen, walk_forward

NUMBERS = ["offer_price", "issue_size_cr", "sub_qib", "sub_hni", "sub_rii", "sub_total"]
REPORT_PATH = REPORTS_DIR / "forward_test.md"
PREDICTIONS_PATH = PROCESSED_DIR / "forward_predictions.csv"
LIVE_FEATURES_PATH = PROCESSED_DIR / "ipo_features_live.csv"
LIVE_MODEL_PATH = MODELS_DIR / "deploy_live.pkl"


def problems(row):
    """What's wrong with one filled-in row (empty list if it's usable)."""
    issues = []
    for col in NUMBERS:
        value = pd.to_numeric(row.get(col), errors="coerce")
        if pd.isna(value):
            issues.append(f"{col} missing")
        elif value <= 0:
            issues.append(f"{col} must be positive")
    if pd.isna(pd.to_numeric(row.get("nse_open"), errors="coerce")):
        issues.append("no listing-day open price")
    if not str(row.get("source_url") or "").strip():
        issues.append("source_url missing")
    if not issues:
        cats = [float(row[c]) for c in ["sub_qib", "sub_hni", "sub_rii"]]
        # total is a weighted average of the categories, so it must sit between them
        if not min(cats) * 0.95 <= float(row["sub_total"]) <= max(cats) * 1.05:
            issues.append("total subscription outside the QIB/HNI/retail range")
    return issues


def to_pipeline_rows(filled):
    """Filled template rows in the same shape as data/interim/ipos_verified.csv."""
    numbers = filled[NUMBERS].apply(pd.to_numeric)
    gain = (pd.to_numeric(filled["nse_open"]) / numbers["offer_price"] - 1) * 100
    return pd.DataFrame({
        "ipo_id": [f"NEW{i:04d}" for i in range(1, len(filled) + 1)],
        "ipo_name": filled["company_name"].to_numpy(),
        "symbol": filled["symbol"].to_numpy(),
        "listing_date": pd.to_datetime(filled["listing_date"]).to_numpy(),
        **{c: numbers[c].to_numpy() for c in NUMBERS},
        "target_gain_pct": gain.to_numpy(),
        "target_source": "nse_open_yahoo",
        "exclude_reason": "",
    })


def load_new_ipos(path=FILLED_PATH):
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame()
    filled = pd.read_csv(path, dtype={"is_mainboard_ipo": str})
    ipos = filled[filled["is_mainboard_ipo"].str.strip().str.lower().eq("yes")]
    if "include" in ipos:  # set by new_ipos_merge after the source and price checks
        ipos = ipos[ipos["include"].eq("yes")]
    ipos = ipos.reset_index(drop=True)
    issues = ipos.apply(problems, axis=1)
    bad = ipos.assign(problems=issues.map("; ".join))[issues.map(bool)]
    return to_pipeline_rows(ipos[~issues.map(bool)].reset_index(drop=True)), bad


def combined_features(new_rows):
    verified = pd.read_csv(VERIFIED_PATH, parse_dates=["listing_date"])
    kept = verified[verified["exclude_reason"].fillna("") == ""]
    table = build_feature_table(pd.concat([kept, new_rows], ignore_index=True),
                                load_index("nifty50"), load_index("india_vix"))
    # appending later IPOs must not change any earlier row's features
    old = pd.read_csv(FEATURES_PATH, parse_dates=["listing_date"])
    pd.testing.assert_frame_equal(table[~table["ipo_id"].str.startswith("NEW")].reset_index(drop=True), old,
                                  check_dtype=False)
    return table.sort_values("listing_date").reset_index(drop=True)


def predict_new(table):
    best = json.loads(BEST_CONFIGS.read_text())
    is_new = table["ipo_id"].str.startswith("NEW")
    out = table.loc[is_new, ["ipo_id", "ipo_name", "listing_date", "sub_total", "sub_rii", TARGET]].copy()
    for name in ["median", "bucket_median", "random_forest"]:
        cfg = best[name]
        out[name] = walk_forward(table, is_new, lambda t, name=name, cfg=cfg: train_model(name, cfg["params"], cfg["data"], t),
                                 columns_for(name, cfg["data"]))

    q_cfg = best["lightgbm"]
    parts = []
    rows = table[is_new]
    for quarter, chunk in rows.groupby(rows["listing_date"].dt.to_period("Q")):
        train = table[table["listing_date"] < quarter.start_time - LAG]
        parts.append(pd.DataFrame(QuantileSet(q_cfg["params"], q_cfg["data"]).fit(train).predict(chunk),
                                  index=chunk.index, columns=["p10", "p50", "p90"]))
    out = out.join(pd.concat(parts))

    # conformal margins keep rolling from the walk-forward history into the new IPOs
    history = pd.read_csv(WF_PREDICTIONS, parse_dates=["listing_date"])[["listing_date", TARGET, "p10", "p90"]]
    both = pd.concat([history, out[["listing_date", TARGET, "p10", "p90"]]], ignore_index=True)
    low, high = conformal_widen(both, both["p10"], both["p90"], coverage=COVERAGE, window=CONFORMAL_WINDOW)
    out["low"], out["high"] = low.iloc[len(history):].to_numpy(), high.iloc[len(history):].to_numpy()
    return out


def report(out, bad):
    rule = json.loads(DECISION_RULE.read_text())
    y = out[TARGET]
    scores = pd.DataFrame([{"model": m, **regression_scores(y, out[m])}
                           for m in ["random_forest", "bucket_median", "median"]]).round(2)
    cover = interval_scores(y, out["low"], out["high"])
    plans = {"Apply to every IPO": out["random_forest"] > -np.inf,
             "Only if 30x+ subscribed": out["sub_total"] >= 30,
             f"Model (gain >= {rule['model_threshold']:+g}%)": out["random_forest"] >= rule["model_threshold"]}
    money = pd.DataFrame([{"strategy": k, **summarize(out, v)} for k, v in plans.items()])
    per_ipo = out[TARGET] / 100 * rule["lot_value"] * out["sub_rii"].map(allotment_chance)
    model_profit = per_ipo.where(list(plans.values())[-1], 0)
    edges = []
    for name in list(plans)[:-1]:
        diff, lo, hi, lose = bootstrap_difference(model_profit, per_ipo.where(plans[name], 0))
        edges.append({"model vs": name, "extra profit": round(diff), "95% low": round(lo), "95% high": round(hi),
                      "resamples where model loses": f"{lose:.0%}"})
    lines = [
        "# Forward test: IPOs listed after the training data",
        f"{len(out)} mainboard IPOs listed {out.listing_date.min():%d %b %Y} – {out.listing_date.max():%d %b %Y}. "
        "Settings, threshold and range method were frozen before these IPOs were added; scored once.",
        "## Accuracy", scores.pipe(markdown_table),
        f"80% range coverage: **{cover['coverage']:.0%}** (average width {cover['avg_width']:.0f} pp).",
        "## Backtest (one lot, allotment lottery)",
        money[["strategy", "applied", "hit_rate", "avg_gain", "expected_profit"]].round(1).pipe(markdown_table),
        "Paired bootstrap (10,000 resamples of the IPOs):", pd.DataFrame(edges).pipe(markdown_table),
    ]
    if len(bad):
        lines += ["## Rows skipped (fix and rerun)", bad[["symbol", "problems"]].pipe(markdown_table)]
    REPORT_PATH.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    return scores, cover, money


def build_live(table, out):
    """App-only artifacts that include the new IPOs: same frozen settings, refit on everything.

    The main pipeline's deploy.pkl and features stay as they are; the app prefers these when present.
    """
    best = json.loads(BEST_CONFIGS.read_text())
    point = best["random_forest"]
    history = pd.read_csv(WF_PREDICTIONS, parse_dates=["listing_date"])[["listing_date", TARGET, "p10", "p90"]]
    recent = pd.concat([history, out[["listing_date", TARGET, "p10", "p90"]]]).sort_values("listing_date")
    deploy = {
        "point_name": "random_forest",
        "point": train_model("random_forest", point["params"], point["data"], table),
        "point_columns": columns_for("random_forest", point["data"]),
        "quantiles": QuantileSet(best["lightgbm"]["params"], best["lightgbm"]["data"]).fit(table),
        "conformal_margin": latest_margin(recent),
        "coverage": COVERAGE,
        "trained_on": {"ipos": len(table), "first": str(table["listing_date"].min().date()),
                       "last": str(table["listing_date"].max().date())},
    }
    joblib.dump(deploy, LIVE_MODEL_PATH)
    table.to_csv(LIVE_FEATURES_PATH, index=False)


def main():
    new_rows, bad = load_new_ipos()
    if new_rows.empty:
        print(f"no usable rows in {FILLED_PATH} yet ({len(bad)} with problems)")
        if len(bad):
            print(bad[["symbol", "problems"]].to_string(index=False))
        return
    table = combined_features(new_rows)
    out = predict_new(table)
    out.to_csv(PREDICTIONS_PATH, index=False)
    build_live(table, out)
    scores, cover, money = report(out, bad)
    print(scores.to_string(index=False))
    print(f"80% range coverage: {cover['coverage']:.0%}")
    print(money[["strategy", "applied", "expected_profit"]].round(0).to_string(index=False))
    print(f"report -> {REPORT_PATH}")


if __name__ == "__main__":
    main()
