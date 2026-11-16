"""Step 1: tune every model family on 2010-2023 with year-by-year validation.

Also scores a model frozen at the end of 2023 on 2024-2026. That number is kept
on purpose: it shows what goes wrong when the model is never refit (see evaluate.py).

    python -m src.models.train
"""

import itertools
import json

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import PROCESSED_DIR, PROJECT_ROOT
from src.models.baselines import BucketMedian, MedianBaseline
from src.models.dataset import FEATURE_SETS, TARGET, load_features, year_folds
from src.models.metrics import regression_scores

MODELS_DIR = PROJECT_ROOT / "models"
BEST_CONFIGS = MODELS_DIR / "best_configs.json"
SEED = 42
TEST_FROM = 2024


def lgbm(**params):
    return LGBMRegressor(learning_rate=0.03, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                         random_state=SEED, verbose=-1, **params)


def ridge(alpha):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=alpha))


def forest(max_depth, min_samples_leaf):
    rf = RandomForestRegressor(n_estimators=400, max_depth=max_depth, min_samples_leaf=min_samples_leaf,
                               max_features=0.5, random_state=SEED, n_jobs=-1)
    return make_pipeline(SimpleImputer(strategy="median"), rf)


def grid(**options):
    return [dict(zip(options, values, strict=True)) for values in itertools.product(*options.values())]


# which features, and how fast old years fade out (half-life in years, None = no fading)
DATA_OPTIONS = grid(features=list(FEATURE_SETS), half_life=[None, 4])

CANDIDATES = {
    "median": (lambda: MedianBaseline(), [{}]),
    "bucket_median": (lambda: BucketMedian(), [{}]),
    "ridge": (ridge, grid(alpha=[0.3, 3, 30])),
    "random_forest": (forest, grid(max_depth=[4, 8], min_samples_leaf=[5, 15])),
    "lightgbm": (lambda **p: lgbm(**p),
                 grid(n_estimators=[200, 500], num_leaves=[7, 15], min_child_samples=[10, 25],
                      objective=["l2", "huber"])),
}
BASELINES = ("median", "bucket_median")


def recency_weights(years, half_life):
    """Weight 1 for the latest year, halving every `half_life` years further back."""
    if half_life is None:
        return None
    years = np.asarray(years)
    return 0.5 ** ((years.max() - years) / half_life)


def fit(model, X, y, weights=None):
    if weights is None:
        return model.fit(X, y)
    if isinstance(model, Pipeline):
        return model.fit(X, y, **{f"{model.steps[-1][0]}__sample_weight": weights})
    return model.fit(X, y, sample_weight=weights)


def columns_for(name, data):
    if name == "median":
        return FEATURE_SETS["base"]
    if name == "bucket_median":
        return ["sub_total"]
    return FEATURE_SETS[data["features"]]


def train_model(name, params, data, frame):
    build, _ = CANDIDATES[name]
    weights = recency_weights(frame["year"], data.get("half_life"))
    return fit(build(**params), frame[columns_for(name, data)], frame[TARGET], weights)


def cross_validate(dev, name, params, data):
    """Out-of-fold predictions for 2019-2023; each fold's model only saw earlier years."""
    preds = pd.Series(np.nan, index=dev.index)
    columns = columns_for(name, data)
    for train_idx, valid_idx in year_folds(dev):
        model = train_model(name, params, data, dev.loc[train_idx])
        preds.loc[valid_idx] = model.predict(dev.loc[valid_idx, columns])
    return preds.dropna()


def tune(dev):
    """Best settings per model family by mean absolute error over the yearly folds."""
    rows, best = [], {}
    for name, (_, param_grid) in CANDIDATES.items():
        data_grid = [{}] if name in BASELINES else DATA_OPTIONS
        for params, data in itertools.product(param_grid, data_grid):
            preds = cross_validate(dev, name, params, data)
            scores = regression_scores(dev.loc[preds.index, TARGET], preds)
            rows.append({"model": name, "params": json.dumps(params), "data": json.dumps(data), **scores})
            if name not in best or scores["mae"] < best[name]["cv_mae"]:
                best[name] = {"params": params, "data": data, "cv_mae": scores["mae"]}
    return pd.DataFrame(rows), best


def main():
    df = load_features()
    dev = df[df["year"] < TEST_FROM].reset_index(drop=True)
    test = df[df["year"] >= TEST_FROM].reset_index(drop=True)
    print(f"tuning on {len(dev)} IPOs (2010-2023)")

    cv_table, best = tune(dev)
    cv_table.sort_values("mae").to_csv(PROCESSED_DIR / "cv_results.csv", index=False)
    MODELS_DIR.mkdir(exist_ok=True)
    BEST_CONFIGS.write_text(json.dumps(best, indent=2))

    frozen = []
    for name, cfg in best.items():
        model = train_model(name, cfg["params"], cfg["data"], dev)
        preds = model.predict(test[columns_for(name, cfg["data"])])
        frozen.append({"model": name, "cv_mae": cfg["cv_mae"], **regression_scores(test[TARGET], preds)})
    frozen = pd.DataFrame(frozen).sort_values("cv_mae")
    frozen.to_csv(PROCESSED_DIR / "frozen_test_results.csv", index=False)

    print("\nbest settings:")
    for name, cfg in best.items():
        print(f"  {name:14s} cv_mae={cfg['cv_mae']:.2f}  {cfg['params']}  {cfg['data']}")
    print("\nfrozen at end of 2023, scored on 2024-2026:")
    print(frozen.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
